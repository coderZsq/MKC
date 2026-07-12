# S4-6 测试用例：引用跳转：点击跳转到 SRT 时间戳 / PDF 页码

## 1. 范围与目标

验证引用跳转功能：CitationCard 点击跳转、路由参数解析、音频 seekTo 与播放、SRT 同步高亮、PDF 页码跳转与 chunk 高亮、错误处理与降级、Web 端兼容性，以及代码质量（覆盖率 80%+、flutter analyze、无硬编码密钥）。

## 2. 测试环境

- Flutter 3.22+ / Dart 3.4+
- flutter_riverpod 2.5+
- dio 5.4+
- go_router 14.1+
- just_audio 0.9+
- pdfrx 1.0+
- Chrome 浏览器（Web 测试）
- mock Gateway 或本地服务

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-6-001 | Functional | Widget | P0 | 点击音频引用卡片构造带参 URI | ChatPage 存在音频 citation | 点击 CitationCard | URI 含 type=audio&t=秒数 | PRD AC-1 |
| MKC-TC-S4-6-002 | Functional | Widget | P0 | 点击 PDF 引用卡片构造带参 URI | ChatPage 存在 PDF citation | 点击 CitationCard | URI 含 type=pdf&page=n&chunk=id | PRD AC-1 |
| MKC-TC-S4-6-003 | Functional | Widget | P0 | 音频引用跳转后 seek 并播放 | 跳转目标 t=120.5 | 进入 ContentViewPage | 播放器 seek 到 120.5s 并播放 | PRD AC-2 |
| MKC-TC-S4-6-004 | Functional | Widget | P0 | 播放过程中 SRT 同步高亮 | 音频播放中 | 监听位置变化 | 当前段字幕高亮 | PRD AC-3 |
| MKC-TC-S4-6-005 | Functional | Widget | P0 | PDF 引用跳转到页码 | 跳转目标 page=3 | 进入 ContentViewPage | 滚动到第 3 页 | PRD AC-4 |
| MKC-TC-S4-6-006 | Functional | Widget | P1 | PDF chunk 文本高亮定位 | 跳转目标含 chunkId | 进入页面 | chunk 文本被高亮 | PRD AC-4 |
| MKC-TC-S4-6-007 | Functional | Unit | P0 | 路由参数 t 解析为秒数 | 查询参数 t=120.5 | 调用 fromQuery | timestampSeconds=120.5 | PRD AC-5 |
| MKC-TC-S4-6-008 | Functional | Unit | P0 | 路由参数 page 解析为整数 | 查询参数 page=3 | 调用 fromQuery | page=3 | PRD AC-5 |
| MKC-TC-S4-6-009 | Functional | Widget | P1 | 跳转后不破坏搜索/折叠 | 已跳转页面 | 使用 TextSearchBar | 搜索与折叠正常 | PRD AC-6 |
| MKC-TC-S4-6-010 | Functional | Integration | P1 | 从 ChatPage 跳转到 ContentViewPage 定位 | 已登录有问答 | 点击引用 | 跳转并定位目标位置 | PRD AC-1,AC-2,AC-4 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-6-011 | Security | Widget | P0 | 未登录跳转登录页 | 无 token | 点击引用卡片 | 跳转登录页 | PRD AC-1 |
| MKC-TC-S4-6-012 | Security | Integration | P1 | Token 过期跳转登录 | 过期 token | 点击引用 | 跳转登录 | 安全基线 |
| MKC-TC-S4-6-013 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |
| MKC-TC-S4-6-014 | Security | Unit | P1 | resourceId 校验非法值 | resourceId 为空 | 构造跳转 | 显示非法提示 | PRD AC-5 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-6-015 | Negative | Unit | P0 | 参数 t 非数字降级 | t=abc | 调用 fromQuery | timestampSeconds=null，降级默认 | PRD AC-5 |
| MKC-TC-S4-6-016 | Negative | Unit | P1 | 参数 page 负数降级 | page=-1 | 调用 fromQuery | page=null，降级第 1 页 | PRD AC-5 |
| MKC-TC-S4-6-017 | Negative | Widget | P0 | 资源 404 显示错误视图 | mock 404 | 点击引用 | 显示错误视图与返回 | PRD AC-7 |
| MKC-TC-S4-6-018 | Negative | Widget | P1 | 音频加载失败显示重试 | mock 失败 | 跳转音频 | 显示重试按钮 | PRD AC-7 |
| MKC-TC-S4-6-019 | Negative | Widget | P1 | chunk 文本未匹配仅跳页 | chunk 不存在 | 跳转 PDF | 仅跳页不高亮 | PRD AC-5 |
| MKC-TC-S4-6-020 | Negative | Unit | P2 | page 超出范围降级 | page=9999 | 调用 fromQuery | 降级第 1 页并提示 | PRD AC-5 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-6-021 | Functional | Static | P1 | flutter analyze 通过 | 代码存在 | 运行 flutter analyze | 0 issues | 工程规范 |
| MKC-TC-S4-6-022 | Functional | Static | P1 | 测试覆盖率 80%+ | 代码存在 | 运行 flutter test --coverage | coverage >= 80% | PRD AC-9 |
| MKC-TC-S4-6-023 | Security | Static | P1 | 无硬编码密钥 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |
| MKC-TC-S4-6-024 | Reliability | Static | P2 | 不可变值对象无 mutation | 代码存在 | 审查 CitationJumpTarget | 字段 final，copyWith 返回新实例 | 工程规范 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S4-6-025 | Compatibility | Widget | P1 | Web 端音频 seek | Chrome 平台 | 运行 flutter test --platform chrome | seek 生效 | PRD AC-8 |
| MKC-TC-S4-6-026 | Compatibility | Widget | P1 | Web 端 PDF 页码跳转 | Chrome 平台 | 运行 flutter test --platform chrome | 跳转生效 | PRD AC-8 |
| MKC-TC-S4-6-027 | Compatibility | E2E | P1 | Web 端引用卡片点击跳转 | Chrome 环境 | 点击引用 | 跳转并定位 | PRD AC-8 |
| MKC-TC-S4-6-028 | Compatibility | E2E | P2 | Web 端 SRT 同步高亮 | Chrome 播放中 | 监听位置 | 高亮跟随 | PRD AC-8 |

## 4. 测试执行清单

- [ ] CitationCard 构造带参 URI
- [ ] 路由参数解析与校验
- [ ] 音频 seekTo 并播放
- [ ] SRT 同步高亮
- [ ] PDF 页码跳转与 chunk 高亮
- [ ] 错误处理与降级
- [ ] Web 端兼容性
- [ ] 测试覆盖率 80%+
- [ ] flutter analyze 通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
