# S1-4 测试用例：Flutter 文件选择/上传页面

## 1. 范围与目标

验证 Flutter 客户端文件上传页面的文件选择、本地校验、上传进度、结果反馈、取消与错误处理符合 PRD/TECH 要求。

## 2. 测试环境

- Flutter 3.22+
- Android/iOS 模拟器、桌面端或 Chrome（Web）
- S1-3 文件上传 API 已启动（集成测试）
- `flutter pub get` 已执行
- Web 测试：`flutter test --platform chrome`；集成测试需 ChromeDriver 与 Gateway CORS 已配置

## 3. 测试用例

### 3.1 文件选择

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-001 | Functional | Widget | P0 | 点击选择按钮调用 FilePicker | 在 UploadPage | 点击“选择文件” | 弹出系统文件选择器 | PRD AC-2 |
| MKC-TC-S1-4-002 | Functional | Widget | P1 | 用户取消选择回到 idle | 选择器打开 | 点击取消 | 页面显示 idle 状态 | PRD AC-2 |
| MKC-TC-S1-4-003 | Functional | Integration | P1 | 选择成功后进入校验 | 已登录 | 选择合法 MP3 | 状态变为 validating | TECH 5 |

### 3.2 本地校验

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-004 | Negative | Widget | P0 | 选择超过 500MB 文件提示过大 | mock picker 返回大文件 | 选择文件 | 显示“文件超过当前平台大小限制” | PRD AC-3 |
| MKC-TC-S1-4-005 | Negative | Widget | P0 | 选择不支持的扩展名提示不支持 | mock picker 返回 `.exe` | 选择文件 | 显示“不支持的文件类型” | PRD AC-3 |
| MKC-TC-S1-4-006 | Functional | Unit | P1 | 白名单扩展名校验通过 | 无 | 校验 `mp3/pdf/docx` | 返回 null | TECH 5 |
| MKC-TC-S1-4-007 | Functional | Unit | P1 | MIME 推断正确 | 无 | 由 `pdf` 推断 `application/pdf` | 返回正确 MIME | TECH 4 |

### 3.3 上传流程

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-008 | Functional | Widget | P0 | 合法文件上传成功 | API 返回 200 | 选择并上传 MP3 | 进度条到 100%，显示 resource_id 与“查看任务” | PRD AC-5 |
| MKC-TC-S1-4-009 | Functional | Widget | P0 | 上传过程中显示进度 | API 支持进度 | 上传文件 | 进度条从 0 递增到 100% | PRD AC-4 |
| MKC-TC-S1-4-010 | Functional | Widget | P1 | 点击取消停止上传 | 上传中 | 点击取消 | dio CancelToken 触发，状态回到 idle | PRD AC-4 |
| MKC-TC-S1-4-011 | Functional | Unit | P1 | 成功后状态为 success | mock repo | 调用 upload | state 为 UploadState.success | TECH 5 |
| MKC-TC-S1-4-012 | Functional | Integration | P0 | 上传成功后跳转任务中心 | API 返回 200 | 点击“查看任务” | 导航到 TaskCenterPage | PRD AC-5 |

### 3.4 错误处理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-013 | Negative | Widget | P0 | 网络错误显示网络异常 | 无网络 | 上传文件 | 显示“网络异常，请检查连接” | PRD AC-6 |
| MKC-TC-S1-4-014 | Negative | Widget | P0 | 服务端 413 显示文件过大 | API 返回 413 | 上传大文件 | 显示“文件过大，请重新选择” | PRD AC-6 |
| MKC-TC-S1-4-015 | Negative | Widget | P0 | 服务端 415 显示不支持 | API 返回 415 | 上传文件 | 显示“服务器不支持该文件类型” | PRD AC-6 |
| MKC-TC-S1-4-016 | Security | Widget | P1 | 401 跳转登录 | API 返回 401，refresh 失败 | 上传文件 | 跳转 LoginPage | PRD AC-7 |
| MKC-TC-S1-4-017 | Negative | Widget | P1 | 未知服务错误显示重试 | API 返回 500 | 上传文件 | 显示“上传失败，请稍后重试”与重试按钮 | PRD AC-6 |

### 3.5 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-018 | Functional | Static | P1 | `flutter analyze` 无错误 | 代码存在 | 运行 `flutter analyze` | 0 issues | 工程规范 |
| MKC-TC-S1-4-019 | Functional | Static | P1 | 无硬编码 API URL 或密钥 | 代码存在 | 全局搜索 | 仅 Env/测试出现 | 安全基线 |
| MKC-TC-S1-4-020 | Functional | Unit | P1 | 大文件上传使用路径而非 bytes | 代码存在 | 检查 `MultipartFile.fromFile` 使用 | 不读取整个文件到内存 | PRD 阻塞风险 |
| MKC-TC-S1-4-021 | Accessibility | Widget | P2 | 进度条有语义标签 | 页面存在 | 检查 `LinearProgressIndicator` semantics | 屏幕阅读器可读 | 可访问性 |

### 3.6 Web 与跨平台兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-4-022 | Compatibility | Widget | P1 | 上传页在 Chrome 正常渲染 | 代码存在 | `flutter test --platform chrome` | 测试通过，无渲染异常 | PRD Web AC |
| MKC-TC-S1-4-023 | Compatibility | Unit | P1 | Web 端 bytes 构建 MultipartFile | mock `PickedFile.bytes` | 调用 `_toMultipartFile` | 使用 `MultipartFile.fromBytes` | TECH 4 |
| MKC-TC-S1-4-024 | Compatibility | Unit | P1 | 移动端 path 构建 MultipartFile | mock `PickedFile.path` | 调用 `_toMultipartFile` | 使用 `MultipartFile.fromFile` | TECH 4 |
| MKC-TC-S1-4-025 | Compatibility | Widget | P1 | Web 端选择大文件提示 ≤100MB | mock picker 返回 150MB | 选择文件 | 显示超过当前平台大小限制 | PRD Web AC |
| MKC-TC-S1-4-026 | Compatibility | Integration | P1 | Web 端选择并上传文件成功 | ChromeDriver | 选择测试文件并上传 | 进度条完成，显示 resource_id | PRD Web AC |

## 4. 测试执行清单

- [ ] 文件选择器调用与取消
- [ ] 文件大小/扩展名校验
- [ ] 合法文件上传成功并显示结果
- [ ] 上传进度更新
- [ ] 取消上传
- [ ] 网络/413/415/401/500 错误提示
- [ ] 成功后跳转任务中心
- [ ] `flutter test` 通过（含 `flutter test --platform chrome` 至少运行一次）
- [ ] `flutter analyze` 0 issues
- [ ] Web 端文件选择/上传集成验证（可选，ChromeDriver）

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
