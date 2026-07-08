# S1-6 测试用例：Flutter 任务中心页面

## 1. 范围与目标

验证 Flutter 任务中心页面在任务列表展示、状态显示、分页加载、下拉刷新、空状态、错误处理与导航上符合 PRD/TECH 要求。

## 2. 测试环境

- Flutter 3.22+
- Android/iOS 模拟器、桌面端或 Chrome（Web）
- S1-5 任务 API 已启动（集成测试）
- `flutter pub get` 已执行
- Web 测试：`flutter test --platform chrome`；集成测试需 ChromeDriver 与 Gateway CORS 已配置

## 3. 测试用例

### 3.1 列表展示

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-001 | Functional | Widget | P0 | 任务列表正常渲染 | mock 3 条任务数据 | 打开 TaskCenterPage | 显示 3 个 TaskListItem | PRD AC-1 |
| MKC-TC-S1-6-002 | Functional | Widget | P0 | 每项显示资源名、状态、进度、更新时间 | mock running 任务 | 查看列表项 | 显示文件名、“处理中”、进度条、时间 | PRD AC-2 |
| MKC-TC-S1-6-003 | Functional | Widget | P1 | 不同状态显示对应颜色标签 | mock pending/running/completed/failed 各一条 | 查看列表 | pending 灰、running 蓝、completed 绿、failed 红 | PRD 状态表 |
| MKC-TC-S1-6-004 | Functional | Widget | P1 | running 任务显示进度条 | mock progress=45 | 查看列表项 | LinearProgressIndicator value=0.45 | PRD AC-2 |
| MKC-TC-S1-6-005 | Functional | Unit | P1 | 状态字符串正确映射枚举 | 无 | 解析各种 status | 映射正确 | TECH 3.2 |

### 3.2 刷新与分页

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-006 | Functional | Widget | P0 | 下拉刷新触发 refresh | mock 列表 | 下拉 | notifier 调用 refresh，列表更新 | PRD AC-3 |
| MKC-TC-S1-6-007 | Functional | Widget | P0 | 滚动到底部加载更多 | mock 20 条数据，第二页 5 条 | 滚动到底部 | 请求 page=2，列表变为 25 条 | PRD AC-4 |
| MKC-TC-S1-6-008 | Functional | Widget | P1 | 加载更多时不重复请求 | 在加载更多中 | 再次滚动到底部 | 只发出一次 page=2 请求 | TECH 5 |
| MKC-TC-S1-6-009 | Functional | Widget | P1 | 无更多数据时停止加载 | 第二页返回空 | 滚动到底部 | hasMore=false，不再请求 | TECH 5 |

### 3.3 空状态与导航

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-010 | Functional | Widget | P0 | 空列表显示占位 | mock 0 条任务 | 打开页面 | 显示“暂无任务”与“去上传”按钮 | PRD AC-5 |
| MKC-TC-S1-6-011 | Functional | Widget | P1 | 点击“去上传”跳转上传页 | 空状态 | 点击按钮 | 导航到 UploadPage | PRD AC-5 |
| MKC-TC-S1-6-012 | Functional | Widget | P1 | 点击任务项跳转详情 | mock 任务 | 点击列表项 | 导航到 TaskDetailPage(id) | PRD AC-6 |

### 3.4 错误处理

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-013 | Negative | Widget | P0 | 网络错误显示重试 | mock 网络异常 | 打开页面 | 显示“网络异常”与重试按钮 | PRD AC-7 |
| MKC-TC-S1-6-014 | Negative | Widget | P0 | 服务端 500 显示重试 | mock 500 | 打开页面 | 显示“加载失败，请稍后重试” | PRD AC-7 |
| MKC-TC-S1-6-015 | Security | Widget | P0 | 401 跳转登录页 | mock 401 | 打开页面 | 跳转 LoginPage | PRD AC-8 |
| MKC-TC-S1-6-016 | Negative | Widget | P1 | 点击重试重新加载 | mock 首次失败第二次成功 | 点击重试 | 列表刷新 | PRD AC-7 |

### 3.5 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-017 | Functional | Static | P1 | `flutter analyze` 无错误 | 代码存在 | 运行 `flutter analyze` | 0 issues | 工程规范 |
| MKC-TC-S1-6-018 | Functional | Static | P1 | 无硬编码 API URL 或密钥 | 代码存在 | 全局搜索 | 仅 Env/测试出现 | 安全基线 |
| MKC-TC-S1-6-019 | Functional | Widget | P1 | 长列表使用 ListView.builder | 代码存在 | 检查页面实现 | 使用 builder，不一次性构建全部 | PRD 阻塞风险 |
| MKC-TC-S1-6-020 | Functional | Integration | P1 | 真实 API 分页与状态一致 | API 有任务 | 打开任务中心 | 列表与后端数据一致 | PRD AC-1 |

### 3.6 Web 与跨平台兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S1-6-021 | Compatibility | Widget | P1 | 任务中心在 Chrome 正常渲染 | 代码存在 | `flutter test --platform chrome` | 测试通过，无渲染异常 | PRD Web AC |
| MKC-TC-S1-6-022 | Compatibility | Widget | P1 | Web 端显式刷新按钮可用 | 代码存在 | 点击“刷新”按钮 | 触发 refresh，列表更新 | TECH 2.1 |
| MKC-TC-S1-6-023 | Compatibility | Widget | P1 | Web 端“加载更多”按钮可用 | mock 第二页数据 | 点击“加载更多” | 请求 page=2，列表追加 | TECH 2.1 |
| MKC-TC-S1-6-024 | Compatibility | Integration | P1 | Web 端任务列表与后端一致 | ChromeDriver | 打开任务中心 | 列表与后端数据一致 | PRD Web AC |

## 4. 测试执行清单

- [ ] 列表渲染与字段显示
- [ ] 状态颜色/进度条显示
- [ ] 下拉刷新
- [ ] 上拉加载更多
- [ ] 空状态与去上传导航
- [ ] 任务项点击进入详情
- [ ] 网络/401/500 错误处理与重试
- [ ] `flutter test` 通过（含 `flutter test --platform chrome` 至少运行一次）
- [ ] `flutter analyze` 0 issues
- [ ] Web 端任务中心集成验证（可选，ChromeDriver）

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
