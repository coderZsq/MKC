# S5-7 测试用例：编写完整 README 与架构文档

## 1. 范围与目标

验证 README、架构文档、部署文档、排障文档的完整性、命令可执行性、链接有效性和敏感信息安全。

## 2. 测试环境

- markdownlint-cli
- markdown-link-check 或 lychee
- 本地 shell
- Docker/K8s 可选环境

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-7-001 | Functional | Static | P0 | README 核心章节完整 | README 存在 | 检查章节 | 含简介/功能/技术栈/快速开始/测试/部署 | PRD AC-1 |
| MKC-TC-S5-7-002 | Functional | Static | P0 | 架构文档组件完整 | ARCHITECTURE 存在 | 检查组件 | 覆盖 Gateway/AI/Client/存储/队列 | PRD AC-2 |
| MKC-TC-S5-7-003 | Functional | Static | P1 | 部署和环境变量说明完整 | DEPLOYMENT 存在 | 检查章节 | 包含本地/K8s/.env.example | PRD AC-3 |
| MKC-TC-S5-7-004 | Functional | Static | P1 | 文档交叉链接完整 | 文档存在 | 运行链接检查 | PRD/TECH/API/runbook 链接有效 | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-7-005 | Security | Static | P0 | 文档无真实密钥 | docs 存在 | 扫描 secret/token/key | 无真实凭据 | PRD AC-6 |
| MKC-TC-S5-7-006 | Security | Static | P1 | 私有域名和个人信息已脱敏 | 文档存在 | 人工检查 | 使用占位符 | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-7-007 | Negative | Static | P1 | 失效链接被检测 | 构造坏链接 | 运行链接检查 | 检查失败并定位链接 | PRD AC-7 |
| MKC-TC-S5-7-008 | Negative | Static | P1 | 不存在命令被发现 | README 命令存在 | 手工/脚本验证 | 不存在命令被修正 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-7-009 | Functional | Static | P0 | markdownlint 通过 | 文档存在 | 运行 markdownlint | 0 issues | PRD AC-7 |
| MKC-TC-S5-7-010 | Functional | Static | P1 | Mermaid 图语法可渲染 | Mermaid 存在 | 预览或 lint | 图可渲染 | PRD AC-2 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-7-011 | Compatibility | Static | P1 | README 包含 Flutter Web 说明 | README 存在 | 检查 Web 章节 | 含 build/run/限制说明 | PRD Web 端适配 |

## 4. 测试执行清单

- [ ] README 章节完整
- [ ] 架构图可渲染
- [ ] 链接检查通过
- [ ] Markdown lint 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
