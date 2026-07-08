# PRD：[S1-6] 实现 Flutter 任务中心页面

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 关联文档：[PRD_S1-5_task_status_api.md](./PRD_S1-5_task_status_api.md)、[TECH_S1-6_flutter_task_center.md](../tech/TECH_S1-6_flutter_task_center.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-6 |
| **任务名称** | 实现 Flutter 任务中心页面 |
| **所属史诗** | E3 任务管理 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-5 任务 API、S1-2 Flutter 认证页面 |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为用户，我需要在 iOS、Android 或 Web（Chrome）端查看所有 AI 处理任务的状态、进度与更新时间，支持刷新与分页加载，并能在任务完成后查看结果或跳转到上传页面新增任务。本任务在 Flutter 客户端实现跨平台任务中心页面。

---

## 验收标准（AC）

- [ ] **AC-1** 任务中心页面展示当前用户的任务列表
- [ ] **AC-2** 每条任务显示：文件名（来自资源）、任务类型、状态标签、进度百分比、更新时间
- [ ] **AC-3** 支持下拉刷新（Pull-to-refresh）
- [ ] **AC-4** 支持上拉分页加载（Infinite scroll）
- [ ] **AC-5** 点击任务项进入任务详情页（Sprint 1 可展示占位详情）
- [ ] **AC-6** 空列表时显示“暂无任务”与“去上传”入口
- [ ] **AC-7** 列表加载/刷新/分页错误时展示友好提示与重试按钮
- [ ] **AC-8** 未登录用户访问任务中心跳转登录页
- [ ] **AC-9** 任务中心在 Web（Chrome）端可正常运行：列表渲染、下拉刷新、分页加载、跳转详情、SSE 进度更新
- [ ] **AC-10** Widget/集成测试覆盖率 80%+（含 `flutter test --platform chrome` 至少运行一次）

---

## 推荐目录结构

```
client/lib/
├── data/
│   ├── datasources/remote/task_api.dart
│   ├── models/task_model.dart
│   └── repositories/task_repository.dart
├── domain/
│   ├── entities/task.dart
│   └── repositories/task_repository.dart
├── presentation/
│   ├── pages/
│   │   ├── task_center_page.dart
│   │   └── task_detail_page.dart      # Sprint 1 占位
│   ├── providers/task_center_provider.dart
│   └── widgets/
│       ├── task_list_item.dart
│       ├── task_status_chip.dart
│       └── task_center_skeleton.dart
└── shared/
    ├── errors/app_exception.dart       # 已存在，复用
    └── result.dart                     # 已存在，复用
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| flutter_riverpod | 2.5.x | 状态管理 |
| dio | 5.4.x | HTTP 请求 |
| go_router | 14.x | 页面路由 |
| freezed | 2.5.x | 不可变状态/模型 |
| intl | 0.19.x | 时间格式化 |

---

## 技术要点

### 状态管理

使用 `AsyncNotifier` 管理分页状态：

- `TaskCenterState` 包含：任务列表、当前页、是否还有更多、是否正在加载更多、错误对象
- `refresh()`：重置为第一页
- `loadMore()`：加载下一页（需避免并发请求）

### 分页策略

- 初始 page=1，limit=20
- 当返回数量等于 limit 时认为可能还有更多
- 加载更多使用 `ScrollController` 监听底部偏移 200px

### 任务状态显示

| 状态 | UI 标签 | 颜色 |
|---|---|---|
| pending | 等待中 | 灰色 |
| running | 处理中 | 蓝色 |
| completed | 已完成 | 绿色 |
| failed | 失败 | 红色 |

### 任务项信息

列表接口返回的 `task_id`、`resource_id`、`type`、`status`、`progress`、`updated_at` 不足以显示文件名，需要同时调用或扩展接口。推荐方案：

- S1-5 列表接口返回 `resource_name` 字段（推荐）
- 备选：前端本地缓存资源信息（S1-4 上传成功后缓存）

Sprint 1 采用推荐方案，要求后端在任务 DTO 中附带 `resource_name`。

### 导航

- 底部/顶部 FAB 或按钮：“上传文件” → 跳转 `UploadPage`
- 点击任务项 → 跳转 `TaskDetailPage`（占位）
- 未登录 → 跳转 `LoginPage`

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| 任务列表缺少资源名 | 用户体验差 | PRD 明确要求后端附带 `resource_name` |
| 任务数量多导致滚动卡顿 | 性能 | 使用 `ListView.builder` + 分页 |

---

## Web 端适配

- 任务中心页面使用 `LayoutBuilder` / `ConstrainedBox` 保证在 Chrome 桌面与移动视口下正常显示；宽屏下可显示更宽松的列表项间距。
- Web 端下拉刷新使用 `RefreshIndicator` 同样支持鼠标拖拽/滚动刷新，或提供显式“刷新”按钮作为辅助。
- Web 端滚动加载更多通过 `ScrollController` 监听底部偏移实现，与移动端一致；同时提供“加载更多”按钮兼容无滚动事件触发的场景。
- Web 端 SSE 实时进度由 S1-7 提供，浏览器使用 `EventSource`；任务中心通过统一封装层监听进度事件并更新对应任务状态。
- Web 端 Dio 请求受浏览器 CORS 限制，要求 Gateway 为任务相关接口配置允许 Flutter Web 域名的跨域头。
- Web 端集成测试使用 ChromeDriver；Widget/单元测试使用 `flutter test --platform chrome`。

---

## 备注

- 任务状态为 running 时，后续通过 S1-7 SSE 实时刷新进度
- Sprint 1 任务详情页仅展示基础字段占位即可
- 列表项长按可删除任务为可选 P2，不在 Sprint 1 范围内
