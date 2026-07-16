# PRD：[S5-10] Flutter 多端适配检查

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 关联文档：[PRD_S3-7_flutter_chat_page.md](./PRD_S3-7_flutter_chat_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S5-10 |
| **任务名称** | Flutter 多端适配检查 |
| **所属史诗** | E12 部署上线 |
| **故事点** | 2 |
| **优先级** | Should |
| **依赖** | S3-7 Flutter Chat 页面 |
| **目标 Sprint** | Sprint 5 |

---

## 描述

作为用户，我希望 MKC 在 iOS、Android 与 Web 上的登录、上传、任务进度、内容查看、问答、引用跳转等主流程都能基础可用，以便在线 Demo 和多端展示时不会因布局、文件选择、SSE 或平台差异中断。

---

## 验收标准（AC）

- [ ] **AC-1** iOS、Android、Web 三端可完成登录、资源列表、上传入口、任务状态和问答主流程
- [ ] **AC-2** 响应式布局适配手机、平板和桌面 Web，文本不溢出、不遮挡核心操作
- [ ] **AC-3** 文件选择与上传在移动端和 Web 端均有平台差异处理与友好错误
- [ ] **AC-4** SSE 或流式回答在三端具备可用降级，断线时给出重试入口
- [ ] **AC-5** PDF/文本/SRT/引用跳转在不同屏幕尺寸下可读可操作
- [ ] **AC-6** Flutter analyze、Widget 测试与 Web build 通过
- [ ] **AC-7** 输出多端兼容性检查清单与已知问题列表

---

## 推荐目录结构

```text
client/
├── lib/core/platform/
│   └── platform_capabilities.dart
├── lib/core/responsive/
│   └── breakpoints.dart
├── test/
│   └── compatibility/
└── integration_test/
    └── smoke_multiplatform_test.dart
docs/runbooks/
└── flutter_multiplatform_checklist.md
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| Flutter | 3.22+ | 多端客户端 |
| Riverpod | 2.x | 状态管理 |
| Dio | 5.x | 网络请求 |
| file_picker | latest | 多端文件选择 |
| flutter_test | SDK | Widget 测试 |

---

## 技术要点

- 统一平台能力判断，避免业务组件到处使用平台分支。
- Web 上传需处理浏览器文件大小、MIME、拖拽和 CORS 限制。
- 移动端长列表、聊天输入框和引用面板需避让键盘与安全区。
- 大屏 Web 使用更宽的信息布局，小屏保持单列优先。
- 已知问题以清单记录，不将非阻塞优化混入本卡。

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Web 与移动端文件 API 差异 | 上传失败 | 平台能力封装与错误文案 |
| SSE 在部分浏览器不稳定 | 回答中断 | 增加重连或普通请求降级 |
| 布局在窄屏溢出 | Demo 观感差 | 增加断点测试和 Widget golden/smoke |

---

## Web 端适配

Web 是本卡重点之一，需要覆盖浏览器文件选择、CORS、SSE、桌面宽屏布局、移动浏览器窄屏布局和静态资源部署路径。

---

## 备注

- 本卡以主流程可用为目标，不追求每个平台的原生体验极致优化。
- 兼容性清单应成为发布前检查项。
