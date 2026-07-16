# S5-4 测试用例：接入 Prometheus + Grafana 监控

## 1. 范围与目标

验证 Prometheus metrics 暴露、指标内容、采集配置、Grafana dashboard、标签安全和部署说明。

## 2. 测试环境

- Go 1.22+
- Python 3.11+
- Prometheus
- Grafana
- pytest / go test

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-4-001 | Functional | Integration | P0 | Gateway /metrics 可访问 | 服务启动 | GET /metrics | 返回 Prometheus 文本 | PRD AC-1 |
| MKC-TC-S5-4-002 | Functional | Integration | P0 | AI Service /metrics 可访问 | 服务启动 | GET /metrics | 返回 AI 指标 | PRD AC-2 |
| MKC-TC-S5-4-003 | Functional | Static | P1 | Prometheus 配置包含服务 | scrape config 存在 | 检查 targets | gateway/ai-service 均存在 | PRD AC-3 |
| MKC-TC-S5-4-004 | Functional | Static | P1 | Grafana 总览看板存在 | dashboard JSON 存在 | 校验 JSON | 包含 QPS/Latency/5xx 面板 | PRD AC-4 |
| MKC-TC-S5-4-005 | Functional | Static | P1 | AI 看板存在 | dashboard JSON 存在 | 校验 JSON | 包含 LLM/Token/任务指标 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-4-006 | Security | Static | P0 | 指标标签无敏感内容 | 产生请求 | 检查 /metrics | 无问题全文/文件名/JWT | PRD AC-6 |
| MKC-TC-S5-4-007 | Security | Static | P1 | metrics 仅内网暴露 | K8s 配置存在 | 检查 Service/Ingress | /metrics 不经公网 Ingress 暴露 | PRD AC-6 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-4-008 | Negative | Unit | P1 | metrics disabled 返回预期状态 | 配置关闭 | GET /metrics | 返回 404 或空注册表 | TECH 7 |
| MKC-TC-S5-4-009 | Negative | Unit | P1 | 指标注册重复可检测 | 构造重复 registry | 启动测试 | 返回 registry error | TECH 7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-4-010 | Functional | Static | P1 | 覆盖率 80%+ | 测试存在 | 运行覆盖率 | coverage >= 80% | PRD AC-8 |
| MKC-TC-S5-4-011 | Functional | Static | P1 | dashboard JSON 格式正确 | dashboard 存在 | 运行 JSON 校验 | 格式合法 | PRD AC-4 |

## 4. 测试执行清单

- [ ] `/metrics` 可访问
- [ ] Prometheus 可采集
- [ ] Grafana 看板 JSON 有效
- [ ] 覆盖率 80%+
- [ ] 静态检查通过

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
