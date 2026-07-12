# S4-3 测试用例：资源卡片展示摘要与标签

## 1. 范围与目标

验证资源列表卡片展示摘要与标签的能力：摘要渲染与折叠/展开、标签 Chip 横向滚动与点击过滤、清除筛选、空状态、错误处理、未登录拦截、代码质量与 Web 端兼容性，确保 PRD AC-1 至 AC-10 全部被覆盖。

## 2. 测试环境

- Flutter 3.22+
- Dart 3.4+
- flutter_riverpod 2.5+
- dio 5.4+
- freezed 2.5+
- intl 0.19+
- Chrome 浏览器（Web 测试）
- mock Gateway 或本地服务

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-3-001 | Functional | Widget | P0 | 卡片正确展示摘要 | 存在含 summary 的资源 | 打开资源列表页 | 卡片显示摘要文本 | PRD AC-1 |
| MKC-TC-S4-3-002 | Functional | Widget | P1 | 空摘要显示占位 | 资源 summary 为 null | 打开资源列表页 | 显示“暂无摘要” | PRD AC-1 |
| MKC-TC-S4-3-003 | Functional | Widget | P0 | 卡片正确展示标签 | 存在含 tags 的资源 | 打开资源列表页 | 标签以 Chip 形式展示 | PRD AC-2 |
| MKC-TC-S4-3-004 | Functional | Widget | P1 | 空标签显示占位 | 资源 tags 为空数组 | 打开资源列表页 | 显示“暂无标签” | PRD AC-2 |
| MKC-TC-S4-3-005 | Functional | Widget | P0 | 摘要默认 2 行折叠 | 摘要长度超过 2 行 | 查看卡片 | 摘要显示 2 行并省略，出现“展开”按钮 | PRD AC-3 |
| MKC-TC-S4-3-006 | Functional | Widget | P0 | 展开/收起切换 | 摘要处于折叠态 | 点击“展开”再点击“收起” | 展开显示完整摘要，收起恢复 2 行 | PRD AC-3 |
| MKC-TC-S4-3-007 | Functional | Widget | P1 | 标签 Chip 横向滚动 | 标签数量超出可视宽度 | 横向滑动 Chip 行 | 可滚动查看全部标签，不换行 | PRD AC-4 |
| MKC-TC-S4-3-008 | Functional | Widget | P0 | 点击标签触发过滤 | 存在含标签的资源 | 点击任一标签 | 列表仅显示含该标签的资源，顶部出现筛选条 | PRD AC-5 |
| MKC-TC-S4-3-009 | Functional | Widget | P1 | 清除筛选恢复全量 | 已选中某标签筛选 | 点击“清除筛选” | tag 清空，恢复全量列表 | PRD AC-5 |
| MKC-TC-S4-3-010 | Functional | Widget | P1 | 资源列表为空显示空状态 | 账户下无资源 | 打开资源列表页 | 显示“暂无资源”空状态 | PRD AC-6 |
| MKC-TC-S4-3-011 | Functional | Widget | P1 | 筛选无结果显示无匹配 | 选中标签无匹配资源 | 点击标签筛选 | 显示“无匹配资源”与清除筛选入口 | PRD AC-6 |
| MKC-TC-S4-3-012 | Functional | Unit | P1 | Repository 实体映射正确 | mock 返回资源 JSON | 调用 fetchResources | summary/tags 字段正确映射为 Resource 实体 | PRD AC-1, AC-2 |
| MKC-TC-S4-3-013 | Performance | Widget | P2 | 长列表滚动不卡顿 | 100 条资源含长摘要 | 快速滚动列表 | 折叠态渲染流畅，无明显丢帧 | PRD AC-3 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-3-014 | Security | Widget | P0 | 未登录跳转登录页 | 无 token | 打开资源列表页 | 跳转至登录页 | PRD AC-8 |
| MKC-TC-S4-3-015 | Security | Integration | P1 | Token 过期跳转登录 | 使用过期 token | 打开资源列表页 | 跳转登录页 | 安全基线 |
| MKC-TC-S4-3-016 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-3-017 | Negative | Widget | P0 | 列表加载失败显示重试 | mock 接口返回 500 | 打开资源列表页 | 显示错误提示与重试按钮 | PRD AC-7 |
| MKC-TC-S4-3-018 | Negative | Widget | P1 | 筛选失败保持原列表 | mock tag 请求失败 | 点击标签筛选 | 保持原列表并提示“筛选失败，请重试” | PRD AC-7 |
| MKC-TC-S4-3-019 | Negative | Widget | P1 | 网络断开友好提示 | 模拟断网 | 打开资源列表页 | 显示“网络异常，请检查连接” + 重试 | PRD AC-7 |
| MKC-TC-S4-3-020 | Negative | Unit | P1 | tag 参数非法被拦截 | 传入空字符串/超长标签 | 调用 fetchResources | 返回 ValidationException，不发起请求 | PRD AC-5 |
| MKC-TC-S4-3-021 | Negative | Widget | P2 | summary 字段缺失不崩溃 | mock 返回无 summary 字段 | 打开资源列表页 | 显示“暂无摘要”，无异常 | PRD AC-1 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-3-022 | Static | Static | P1 | flutter analyze 通过 | 代码存在 | 运行 flutter analyze | 0 issues | 工程规范 |
| MKC-TC-S4-3-023 | Static | Static | P1 | Widget 测试覆盖率 80%+ | 代码存在 | 运行 flutter test --coverage | coverage >= 80% | PRD AC-10 |
| MKC-TC-S4-3-024 | Security | Static | P1 | 无 hardcoded 密钥 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-3-025 | Compatibility | Widget | P1 | Web 端卡片渲染一致 | Chrome 平台 | 运行 flutter test --platform chrome | 卡片摘要与标签正常渲染 | PRD AC-9 |
| MKC-TC-S4-3-026 | Compatibility | Widget | P1 | Web 端 Chip 横向滚动 | Chrome 平台、标签超宽 | 鼠标拖拽 Chip 行 | 可横向滚动查看全部标签 | PRD AC-9 |
| MKC-TC-S4-3-027 | Compatibility | E2E | P1 | Web 端标签过滤交互 | Chrome 环境 | 点击标签筛选并清除 | 列表正确过滤与恢复 | PRD AC-9 |
| MKC-TC-S4-3-028 | Compatibility | E2E | P2 | Web 端展开/收起交互 | Chrome 环境 | 点击展开与收起 | 摘要正确切换显示 | PRD AC-9 |

## 4. 测试执行清单

- [ ] 摘要渲染与空摘要占位
- [ ] 标签渲染与空标签占位
- [ ] 摘要 2 行折叠与展开/收起
- [ ] 标签 Chip 横向滚动
- [ ] 标签点击过滤与清除筛选
- [ ] 空状态与筛选无结果
- [ ] 加载/筛选失败重试
- [ ] 未登录与 Token 过期跳转
- [ ] Web 端渲染与交互兼容
- [ ] Widget 测试覆盖率 80%+
- [ ] flutter analyze 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
