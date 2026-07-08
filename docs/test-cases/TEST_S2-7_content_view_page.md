# S2-7 测试用例：Flutter 内容查看页（SRT/文本）

## 1. 范围与目标

验证 Flutter 内容查看页：SRT 解析、PDF 文本展示、搜索高亮、时间戳/页码跳转、错误处理与 Web 端兼容。

## 2. 测试环境

- Flutter 3.22+
- Android/iOS 模拟器、桌面端或 Chrome（Web）
- S2-6 结果 API 已启动
- 测试 SRT 与 PDF 解析结果文件

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-7-001 | Functional | Widget | P0 | 内容查看页正常渲染 | mock 任务数据 | 打开 ContentViewPage | 页面加载成功 | PRD AC-1 |
| MKC-TC-S2-7-002 | Functional | Unit | P0 | SRT 解析正确 | 提供标准 SRT | 调用 parseSrt | 返回正确 segments | PRD AC-2 |
| MKC-TC-S2-7-003 | Functional | Widget | P0 | SRT 列表展示时间戳与文本 | mock SRT | 打开音频内容页 | 显示时间戳与文本 | PRD AC-2 |
| MKC-TC-S2-7-004 | Functional | Widget | P0 | 点击时间戳跳转音频 | mock 音频播放器 | 点击时间戳 | 播放器 seek 到对应位置 | PRD AC-2 |
| MKC-TC-S2-7-005 | Functional | Widget | P0 | PDF 文本按页折叠展示 | mock PDF 解析结果 | 打开 PDF 内容页 | 显示页码与折叠面板 | PRD AC-3 |
| MKC-TC-S2-7-006 | Functional | Widget | P1 | 文本搜索高亮 | 输入关键词 | 调用搜索 | 匹配文本高亮 | PRD AC-4 |
| MKC-TC-S2-7-007 | Functional | Widget | P1 | 上一个/下一个匹配跳转 | 搜索结果存在 | 点击导航 | 列表滚动到对应位置 | PRD AC-4 |
| MKC-TC-S2-7-008 | Functional | Widget | P1 | 切换原文/清洗文本 | 音频任务 | 点击切换 | 展示不同文本 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-7-009 | Security | Integration | P0 | 无权限任务无法查看 | 其他用户任务 | 打开内容页 | 显示 404/无权限 | PRD 权限 |
| MKC-TC-S2-7-010 | Security | Static | P1 | 无硬编码 API URL 或密钥 | 代码存在 | 全局搜索 | 仅 Env/测试出现 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-7-011 | Negative | Widget | P0 | 下载失败显示重试 | mock 网络异常 | 打开页面 | 显示重试按钮 | PRD AC-6 |
| MKC-TC-S2-7-012 | Negative | Widget | P1 | 解析失败显示错误 | 提供非法内容 | 打开页面 | 显示“内容格式错误” | TECH 7 |
| MKC-TC-S2-7-013 | Negative | Widget | P1 | 任务未完成显示处理中 | 任务 running | 打开页面 | 显示“处理中” | TECH 7 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-7-014 | Functional | Static | P1 | `flutter analyze` 无错误 | 代码存在 | 运行 `flutter analyze` | 0 issues | 工程规范 |
| MKC-TC-S2-7-015 | Functional | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 | 仅 Env 出现 | 安全基线 |
| MKC-TC-S2-7-016 | Functional | Widget | P1 | 长列表使用 ListView.builder | 代码存在 | 检查页面 | 使用 builder | 阻塞风险 |

### 3.5 Web 与跨平台兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-7-017 | Compatibility | Widget | P1 | 内容页在 Chrome 正常渲染 | 代码存在 | `flutter test --platform chrome` | 测试通过 | PRD Web 适配 |
| MKC-TC-S2-7-018 | Compatibility | Widget | P1 | Web 端搜索框正常输入 | 代码存在 | 输入关键词 | 触发搜索 | PRD Web 适配 |
| MKC-TC-S2-7-019 | Compatibility | Integration | P1 | Web 端查看 PDF 文本 | ChromeDriver | 打开 PDF 任务 | 文本展示正确 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] 内容页渲染
- [ ] SRT 解析与列表展示
- [ ] 时间戳跳转
- [ ] PDF 文本折叠展示
- [ ] 搜索高亮与跳转
- [ ] 原文/清洗切换
- [ ] 错误处理与重试
- [ ] `flutter test` 通过（含 Chrome）
- [ ] `flutter analyze` 0 issues
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
