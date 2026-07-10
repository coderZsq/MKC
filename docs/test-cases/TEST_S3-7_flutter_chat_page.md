# S3-7 测试用例：Flutter AI 对话页面

## 1. 范围与目标

验证 Flutter AI 对话页面：页面渲染、消息列表、流式消息显示、Markdown 渲染、引用卡片、多轮对话、会话切换、错误处理与 Web 端兼容性。

## 2. 测试环境

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5+
- dio 5.4+
- flutter_markdown 0.7+
- chrome 浏览器（Web 测试）
- mock Gateway 或本地服务

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-7-001 | Functional | Widget | P0 | 消息列表正确展示 | 存在历史消息 | 打开 ChatPage | 用户与助手消息正确渲染 | PRD AC-1 |
| MKC-TC-S3-7-002 | Functional | Widget | P0 | 发送问题后显示流式答案 | 已登录 | 输入问题并发送 | 看到答案逐字出现 | PRD AC-3 |
| MKC-TC-S3-7-003 | Functional | Widget | P1 | Markdown 渲染加粗/列表/代码 | 答案含 Markdown | 查看消息 | 渲染为对应格式 | PRD AC-4 |
| MKC-TC-S3-7-004 | Functional | Widget | P1 | 引用卡片显示来源 | 答案含 citation | 查看消息 | 引用卡片可点击 | PRD AC-5 |
| MKC-TC-S3-7-005 | Functional | Widget | P1 | 多轮对话保留历史 | 已有问答 | 继续提问 | 上下文包含历史 | PRD AC-6 |
| MKC-TC-S3-7-006 | Functional | Widget | P1 | 新建/切换/删除会话 | 会话列表页 | 操作列表 | 会话状态同步 | PRD AC-7 |
| MKC-TC-S3-7-007 | Functional | Unit | P2 | 取消正在生成的答案 | 流式中 | 点击取消 | SSE 订阅取消，停止更新 | PRD AC-8 |
| MKC-TC-S3-7-008 | Functional | Widget | P2 | 空消息不可发送 | 输入框为空 | 点击发送 | 发送按钮禁用 | PRD AC-2 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-7-009 | Security | Widget | P0 | 未登录跳转登录页 | 无 token | 打开 ChatPage | 跳转至登录 | PRD AC-1 |
| MKC-TC-S3-7-010 | Security | Integration | P1 | Token 过期后刷新失败 | 使用过期 token | 提问 | 跳转登录 | 安全基线 |
| MKC-TC-S3-7-011 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-7-012 | Negative | Widget | P0 | 加载失败显示重试 | mock 失败 | 打开 ChatPage | 显示重试按钮 | PRD AC-8 |
| MKC-TC-S3-7-013 | Negative | Widget | P1 | 发送失败显示重试 | 网络错误 | 发送问题 | 显示错误提示 | PRD AC-8 |
| MKC-TC-S3-7-014 | Negative | Widget | P1 | SSE 断开后降级轮询 | 模拟断网 | 提问 | 自动轮询获取状态 | PRD AC-8 |
| MKC-TC-S3-7-015 | Negative | Unit | P1 | 流式 error 事件停止生成 | 模拟 error 事件 | 消费 SSE | 停止流式，显示错误 | PRD AC-8 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-7-016 | Functional | Static | P1 | flutter analyze 通过 | 代码存在 | 运行 flutter analyze | 0 issues | 工程规范 |
| MKC-TC-S3-7-017 | Functional | Static | P1 | 测试覆盖率 80%+ | 代码存在 | 运行 flutter test --coverage | coverage >= 80% | PRD AC-9 |
| MKC-TC-S3-7-018 | Security | Static | P1 | 无 hardcoded 密钥 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S3-7-019 | Compatibility | Widget | P1 | Web 端渲染消息列表 | Chrome 平台 | 运行 flutter test --platform chrome | 通过 | PRD AC-9 |
| MKC-TC-S3-7-020 | Compatibility | E2E | P1 | Web 端输入框与键盘兼容 | Chrome 环境 | 输入长问题 | 可正常发送 | PRD Web 适配 |
| MKC-TC-S3-7-021 | Compatibility | E2E | P2 | 引用卡片点击跳转 | Chrome 环境 | 点击引用 | 跳转资源页 | PRD AC-5 |

## 4. 测试执行清单

- [ ] 消息列表与气泡渲染
- [ ] 流式答案显示
- [ ] Markdown 与引用卡片
- [ ] 多轮对话与历史加载
- [ ] 会话管理
- [ ] 错误处理与重试
- [ ] Web 端兼容性
- [ ] 测试覆盖率 80%+
- [ ] flutter analyze 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
