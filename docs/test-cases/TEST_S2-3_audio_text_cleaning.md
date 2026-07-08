# S2-3 测试用例：音频文本清洗（语气词/重复）

## 1. 范围与目标

验证音频转录文本清洗服务：规则清洗效果、LLM 清洗调用、时间戳保持、失败降级与代码质量。

## 2. 测试环境

- Python 3.11+
- 智谱 GLM-4 / Kimi API key（集成测试）
- 测试 segments 数据

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-3-001 | Functional | Unit | P0 | 语气词被删除 | 文本含“嗯”“啊” | 调用 rule_cleaner | 文本无语气词 | PRD AC-2 |
| MKC-TC-S2-3-002 | Functional | Unit | P0 | 重复词被合并 | 文本含“是是是” | 调用 rule_cleaner | 输出“是” | PRD AC-2 |
| MKC-TC-S2-3-003 | Functional | Unit | P1 | 时间戳保持不变 | 提供 segments | 调用 service.clean | 时间戳不变 | PRD AC-4 |
| MKC-TC-S2-3-004 | Functional | Integration | P1 | LLM 清洗模式生效 | 配置 mode=llm | 调用 service | 调用 LLM 并返回结果 | PRD AC-3 |
| MKC-TC-S2-3-005 | Functional | Integration | P1 | 清洗后重新生成 SRT | 提供 segments | 调用清洗 + SRT 生成 | SRT 文本为清洗后结果 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-3-006 | Security | Static | P1 | 无硬编码 LLM API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |
| MKC-TC-S2-3-007 | Security | Integration | P1 | LLM 调用失败不暴露 key | 模拟错误 | 查看日志 | 无 key 泄露 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-3-008 | Negative | Unit | P0 | 清洗失败 fallback 到原文 | 配置 fallback_on_error | 模拟 LLM 异常 | 返回原始文本 | PRD AC-6 |
| MKC-TC-S2-3-009 | Negative | Unit | P1 | 清洗后为空回退原文 | 文本全是语气词 | 调用清洗 | 返回原始文本 | TECH 7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-3-010 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-3-011 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-3-012 | Compatibility | Widget | P2 | 查看页可切换原文/清洗 | 页面存在 | 点击切换 | 文本正确切换 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] 规则清洗效果
- [ ] LLM 清洗调用
- [ ] 时间戳保持
- [ ] 失败 fallback
- [ ] SRT 重新生成
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
