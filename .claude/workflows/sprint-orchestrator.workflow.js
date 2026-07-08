export const meta = {
  name: 'sprint-orchestrator',
  description: '按顺序驱动 Sprint 内所有 Must 任务卡：逐张开发、E2E 测试，失败即停止',
  phases: [
    { title: 'Discover', detail: '解析 AGILE 计划，获取 Sprint 任务卡列表' },
    { title: 'Develop & Test', detail: '顺序执行开发 Agent 与 E2E 测试 Agent' },
  ],
}

const SPRINT = args.sprint
const AGILE_PLAN = args.agilePlanPath || 'docs/AGILE_plan_multimedia_knowledge_assistant.md'
const BASE_BRANCH = args.baseBranch || 'main'
const BASE_URL = args.baseUrl || 'http://localhost:8080/api/v1'
const AI_SERVICE_URL = args.aiServiceUrl || 'http://localhost:5000/api/v1'
const MAX_CARDS = args.maxCards || null

if (!SPRINT) {
  throw new Error('缺少必需参数 args.sprint，例如 args: { sprint: "S2" }')
}

// ---------------------------------------------------------------------------
// Phase 1: Discover
// ---------------------------------------------------------------------------
phase('Discover')

log(`解析 Sprint ${SPRINT} 的任务卡...`)

const discoverSchema = {
  type: 'object',
  properties: {
    cards: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: '任务卡编号，例如 S2-1' },
          name: { type: 'string', description: '任务名称' },
          priority: { type: 'string', description: 'Must / Should / Could' },
          points: { type: 'number' },
          dependencies: { type: 'string' },
          epic: { type: 'string' },
        },
        required: ['id', 'name', 'priority'],
      },
    },
  },
  required: ['cards'],
}

const discovery = await agent(
  `读取 ${AGILE_PLAN}，提取 Sprint ${SPRINT} 章节中所有任务卡。` +
  `只返回该 Sprint 表格里的任务卡，包含：id、name、priority、points、dependencies、epic。` +
  `按 id 自然顺序排序后返回。`,
  { phase: 'Discover', schema: discoverSchema }
)

let mustCards = discovery.cards.filter(c => c.priority === 'Must')
mustCards.sort((a, b) => a.id.localeCompare(b.id))

if (MAX_CARDS) {
  mustCards = mustCards.slice(0, MAX_CARDS)
}

log(`发现 ${mustCards.length} 张 Must 卡：${mustCards.map(c => c.id).join(', ')}`)

if (mustCards.length === 0) {
  return { message: `Sprint ${SPRINT} 没有 Must 任务卡，无需执行。` }
}

// ---------------------------------------------------------------------------
// Phase 2: Develop & Test
// ---------------------------------------------------------------------------
phase('Develop & Test')

const results = []
let stopped = false

for (const card of mustCards) {
  if (stopped) break

  log(`\n========== 开始处理 ${card.id}: ${card.name} ==========`)

  // 1. 推断文档路径与受影响模块
  const infoSchema = {
    type: 'object',
    properties: {
      prdPath: { type: 'string' },
      techPath: { type: 'string' },
      testPath: { type: 'string' },
      shortName: { type: 'string' },
      modules: { type: 'array', items: { type: 'string' } },
    },
    required: ['prdPath', 'techPath', 'testPath', 'shortName', 'modules'],
  }

  const info = await agent(
    `在 ${AGILE_PLAN} 同目录的 docs/prd/、docs/tech/、docs/test-cases/ 下查找 ${card.id} 对应的文档。` +
    `推断文件实际路径（如 docs/prd/PRD_${card.id}_xxx.md）。` +
    `然后读取 PRD 和 TECH，判断涉及哪些模块：gateway、client、ai-service。` +
    `返回 prdPath、techPath、testPath、shortName、modules。`,
    { phase: 'Develop & Test', schema: infoSchema }
  )

  log(`${card.id} 受影响模块：${info.modules.join(', ')}`)

  // 2. 调用 feature-developer 完成开发
  const devSchema = {
    type: 'object',
    properties: {
      status: { type: 'string', enum: ['success', 'blocked'] },
      branch: { type: 'string' },
      prUrl: { type: 'string' },
      notes: { type: 'string' },
    },
    required: ['status', 'branch', 'prUrl', 'notes'],
  }

  const dev = await agent(
    `你先读取 .claude/agents/feature-developer.md，然后完全按照该 Agent 的角色与流程执行。\n` +
    `输入参数：\n` +
    `- PRD_PATH: ${info.prdPath}\n` +
    `- TECH_PATH: ${info.techPath}\n` +
    `- TEST_CASES_PATH: ${info.testPath}\n` +
    `- FEATURE_ID: ${card.id}\n` +
    `- AFFECTED_MODULES: ${info.modules.join(',')}\n` +
    `- BASE_BRANCH: ${BASE_BRANCH}\n\n` +
    `完成后返回 JSON：status（success/blocked）、branch、prUrl、notes。`,
    { phase: 'Develop & Test', schema: devSchema }
  )

  if (dev.status !== 'success') {
    results.push({
      card,
      stage: 'develop',
      status: 'blocked',
      branch: dev.branch,
      prUrl: dev.prUrl,
      notes: dev.notes,
    })
    log(`${card.id} 开发阶段阻塞，停止编排。`)
    stopped = true
    break
  }

  log(`${card.id} 开发完成，PR: ${dev.prUrl}`)

  // 3. 调用 e2e-tester 执行端到端测试
  const e2eSchema = {
    type: 'object',
    properties: {
      status: { type: 'string', enum: ['pass', 'fail'] },
      passedCases: { type: 'array', items: { type: 'string' } },
      failedCases: { type: 'array', items: { type: 'string' } },
      notes: { type: 'string' },
    },
    required: ['status', 'passedCases', 'failedCases', 'notes'],
  }

  const e2e = await agent(
    `你先读取 .claude/agents/e2e-tester.md，然后完全按照该 Agent 的角色与流程执行。\n` +
    `输入参数：\n` +
    `- PRD_PATH: ${info.prdPath}\n` +
    `- TECH_PATH: ${info.techPath}\n` +
    `- TEST_CASES_PATH: ${info.testPath}\n` +
    `- FEATURE_BRANCH: ${dev.branch}\n` +
    `- BASE_URL: ${BASE_URL}\n` +
    `- AI_SERVICE_URL: ${AI_SERVICE_URL}\n\n` +
    `完成后返回 JSON：status（pass/fail）、passedCases、failedCases、notes。`,
    { phase: 'Develop & Test', schema: e2eSchema }
  )

  results.push({
    card,
    stage: 'e2e',
    status: e2e.status,
    branch: dev.branch,
    prUrl: dev.prUrl,
    passedCases: e2e.passedCases,
    failedCases: e2e.failedCases,
    notes: e2e.notes,
  })

  if (e2e.status !== 'pass') {
    log(`${card.id} E2E 测试失败，停止编排。`)
    stopped = true
    break
  }

  log(`${card.id} E2E 通过，继续下一张卡。`)
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------
const passed = results.filter(r => r.status === 'pass').length
const blocked = results.filter(r => r.status === 'blocked' || r.status === 'fail').length

const reportLines = [
  `## Sprint ${SPRINT} 编排结果`,
  '',
  `- 计划执行 Must 卡：${mustCards.length} 张`,
  `- 成功通过 E2E：${passed} 张`,
  `- 阻塞/失败：${blocked} 张`,
  '',
  '### 状态明细',
  '',
  '| 任务卡 | 名称 | 状态 | PR | E2E |',
  '|---|---|---|---|---|',
]

for (const r of results) {
  const statusEmoji = r.status === 'pass' ? '✅' : '❌'
  const e2eEmoji = r.status === 'pass' ? '✅ pass' : '❌ fail/blocked'
  reportLines.push(`| ${r.card.id} | ${r.card.name} | ${statusEmoji} ${r.status} | [PR](${r.prUrl}) | ${e2eEmoji} |`)
}

if (blocked > 0) {
  const blockedItem = results.find(r => r.status !== 'pass')
  reportLines.push(
    '',
    '### 阻塞详情',
    '',
    `- **任务卡**：${blockedItem.card.id} - ${blockedItem.card.name}`,
    `- **阶段**：${blockedItem.stage}`,
    `- **分支**：${blockedItem.branch}`,
    `- **PR**：${blockedItem.prUrl}`,
    `- **备注**：${blockedItem.notes}`,
  )
}

const remaining = mustCards.slice(results.length)
if (remaining.length > 0) {
  reportLines.push(
    '',
    '### 未执行卡片',
    '',
    ...remaining.map(c => `- ${c.id}: ${c.name}`),
  )
}

const report = reportLines.join('\n')
log('\n' + report)

return {
  sprint: SPRINT,
  total: mustCards.length,
  passed,
  blocked,
  results,
  report,
}
