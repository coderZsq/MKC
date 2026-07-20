# S6-2 测试用例：引入 LlamaIndex 依赖与配置开关

## 1. 范围与目标

验证 LlamaIndex 依赖声明、`RAG_ENGINE` 配置解析、默认 legacy、非法值报错和依赖缺失降级。

## 2. 测试环境

- Python 3.11+
- pytest
- ruff / mypy
- 可选无 LlamaIndex 依赖环境

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-2-001 | Functional | Static | P0 | LlamaIndex 依赖已声明 | requirements 存在 | 检查依赖文件 | 包含 llama-index-core | PRD AC-1 |
| MKC-TC-S6-2-002 | Functional | Unit | P0 | 默认 RAG_ENGINE 为 legacy | 无环境变量 | 构建配置 | engine=legacy | PRD AC-2 |
| MKC-TC-S6-2-003 | Functional | Unit | P0 | 环境变量可切 llamaindex | 设置 RAG_ENGINE=llamaindex | 构建配置 | engine=llamaindex | PRD AC-3 |
| MKC-TC-S6-2-004 | Functional | Unit | P1 | legacy 模式不强制加载 LlamaIndex | 模拟依赖缺失 | 构建 legacy 配置 | 不报错 | PRD AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-2-005 | Security | Static | P1 | 配置文件无硬编码 Key | 代码存在 | 搜索 key/token/secret | 无真实密钥 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-2-006 | Negative | Unit | P0 | 非法 RAG_ENGINE 被拒绝 | RAG_ENGINE=bad | 构建配置 | 返回 RAG_ENGINE_INVALID | PRD AC-3 |
| MKC-TC-S6-2-007 | Negative | Unit | P1 | llamaindex 模式依赖缺失报错清晰 | 模拟 ImportError | require_llamaindex | 返回 RAG_ENGINE_UNAVAILABLE | PRD AC-4 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S6-2-008 | Functional | Static | P1 | pytest 覆盖率 80%+ | 测试存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-6 |
| MKC-TC-S6-2-009 | Functional | Static | P1 | ruff/mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |

## 4. 测试执行清单

- [ ] 默认 legacy
- [ ] llamaindex 可切换
- [ ] 非法配置报错
- [ ] legacy 可无 LlamaIndex 启动
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
