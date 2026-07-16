# S5-10 测试用例：Flutter 多端适配检查

## 1. 范围与目标

验证 Flutter iOS、Android、Web 三端登录、上传、任务、问答、引用跳转、响应式布局、SSE 降级和发布前兼容性清单。

## 2. 测试环境

- Flutter 3.22+
- iOS Simulator / Android Emulator / Chrome
- flutter_test
- integration_test
- mock API 或本地 Gateway

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-10-001 | Functional | E2E | P0 | 三端登录流程可用 | 三端环境就绪 | 执行登录 | 登录成功进入首页 | PRD AC-1 |
| MKC-TC-S5-10-002 | Functional | E2E | P0 | 三端问答主流程可用 | 已有资源 | 发起问题 | 返回答案 | PRD AC-1 |
| MKC-TC-S5-10-003 | Functional | Widget | P1 | 响应式布局不溢出 | 设置多种宽度 | 渲染主页面 | 无 overflow | PRD AC-2 |
| MKC-TC-S5-10-004 | Functional | Integration | P1 | 多端文件选择可用 | mock file_picker | 选择文件 | 返回文件元信息 | PRD AC-3 |
| MKC-TC-S5-10-005 | Functional | Integration | P1 | 引用跳转可读可操作 | 答案含 citation | 点击引用 | 跳到 PDF/SRT/文本位置 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-10-006 | Security | Integration | P0 | 未登录访问被拦截 | 清空 token | 打开资源页 | 跳转登录或显示认证错误 | 安全要求 |
| MKC-TC-S5-10-007 | Security | Static | P0 | Web build 不含 API Key | build web | 扫描产物 | 无模型 Key/JWT secret | 安全要求 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-10-008 | Negative | Widget | P1 | 文件选择失败提示友好 | mock picker 抛错 | 点击上传 | 显示错误提示 | PRD AC-3 |
| MKC-TC-S5-10-009 | Negative | Integration | P1 | SSE 断线可重试 | mock stream disconnect | 发起问答 | 显示重试入口 | PRD AC-4 |
| MKC-TC-S5-10-010 | Negative | Widget | P1 | 窄屏键盘不遮挡输入 | 移动端尺寸 | 聚焦输入框 | 输入框可见 | PRD AC-2 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-10-011 | Functional | Static | P0 | flutter analyze 通过 | client 存在 | 运行 flutter analyze | 0 issues | PRD AC-6 |
| MKC-TC-S5-10-012 | Functional | Static | P0 | flutter test 通过 | 测试存在 | 运行 flutter test | 全部通过 | PRD AC-6 |
| MKC-TC-S5-10-013 | Functional | Static | P0 | flutter build web 通过 | Web 配置存在 | 运行 build web | 构建成功 | PRD AC-6 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S5-10-014 | Compatibility | E2E | P0 | Chrome Web 主流程可用 | Web build 部署 | 登录、上传、问答 | 主流程成功 | PRD Web 端适配 |
| MKC-TC-S5-10-015 | Compatibility | Widget | P1 | 桌面宽屏布局合理 | 宽度 1440 | 渲染页面 | 信息分栏合理无遮挡 | PRD AC-2 |
| MKC-TC-S5-10-016 | Compatibility | Widget | P1 | 移动浏览器窄屏布局合理 | 宽度 390 | 渲染页面 | 单列布局无溢出 | PRD AC-2 |

## 4. 测试执行清单

- [ ] iOS/Android/Web 主流程通过
- [ ] flutter analyze 通过
- [ ] flutter test 通过
- [ ] flutter build web 通过
- [ ] 兼容性清单更新

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
