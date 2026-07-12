# PRD：[S4-3] 资源卡片展示摘要与标签

> 版本：v1.0
> 日期：2026-07-12
> 作者：朱双泉
> 关联文档：[PRD_S4-1_summary_extraction.md](./PRD_S4-1_summary_extraction.md)、[PRD_S4-2_tag_entity_extraction.md](./PRD_S4-2_tag_entity_extraction.md)、[PRD_S1-6_flutter_task_center.md](./PRD_S1-6_flutter_task_center.md)、[PRD_S2-7_content_view_page.md](./PRD_S2-7_content_view_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S4-3 |
| **任务名称** | 资源卡片展示摘要与标签 |
| **所属史诗** | E8 智能抽取 |
| **故事点** | 2 |
| **优先级** | Should |
| **依赖** | S4-1 全文/章节摘要提取、S4-2 标签/实体抽取、S1-6 Flutter 任务中心页面（资源列表骨架） |
| **目标 Sprint** | Sprint 4 |

---

## 描述

作为用户，我希望在资源列表卡片中直接看到由 S4-1 提取的摘要和 S4-2 抽取的标签，以便无需逐条进入详情即可快速判断资源内容，并能够通过点击标签快速过滤出相关资源。本任务升级 Flutter 资源列表卡片，复用 S1-6 的列表骨架，新增摘要折叠/展开与标签 Chip 横向滚动能力，并对接 Gateway `GET /api/v1/resources` 返回的 `summary` 与 `tags` 字段。

---

## 验收标准（AC）

- [ ] **AC-1** 资源列表卡片展示每条资源的摘要（`summary`）字段，摘要为空时显示“暂无摘要”占位
- [ ] **AC-2** 资源列表卡片展示每条资源的标签（`tags`）字段，标签为空时显示“暂无标签”占位
- [ ] **AC-3** 摘要默认以 2 行折叠显示，超出部分以省略号截断，提供“展开/收起”切换以查看完整摘要
- [ ] **AC-4** 标签以 Chip 形式横向滚动展示，标签数量超出可视宽度时可滑动查看全部
- [ ] **AC-5** 点击任一标签后，列表仅展示包含该标签的资源（通过 `tag` 查询参数请求 Gateway），并在顶部显示当前筛选标签与“清除筛选”入口
- [ ] **AC-6** 资源列表为空或筛选结果为空时，显示“暂无资源”/“无匹配资源”空状态
- [ ] **AC-7** 列表加载失败时展示友好错误提示与重试按钮
- [ ] **AC-8** 未登录用户访问资源列表跳转登录页
- [ ] **AC-9** Web（Chrome）端卡片渲染一致，Chip 溢出可横向滚动，使用 `flutter test --platform chrome` 验证至少运行一次
- [ ] **AC-10** Widget/集成测试覆盖率 80%+

---

## 推荐目录结构

```
client/lib/
├── data/
│   ├── datasources/remote/resource_api.dart
│   ├── models/resource_model.dart
│   └── repositories/resource_repository.dart
├── domain/
│   ├── entities/resource.dart
│   └── repositories/resource_repository.dart
├── presentation/
│   ├── pages/resource_list_page.dart
│   ├── providers/resource_list_provider.dart
│   └── widgets/
│       ├── resource_card.dart
│       ├── resource_summary_text.dart
│       └── tag_chip_row.dart
└── shared/
    └── errors/app_exception.dart       # 已存在，复用
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

### 数据模型

```dart
@freezed
class Resource with _$Resource {
  const factory Resource({
    required String id,
    required String name,
    required String type,          // audio / pdf / document
    required String status,
    required String? summary,
    @Default(false) bool summaryTruncated,
    @Default([]) List<String> tags,
    required DateTime updatedAt,
  }) = _Resource;
}
```

### 响应示例 JSON

```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "resource_id": "res_001",
        "name": "产品周会-20260701.mp3",
        "type": "audio",
        "status": "completed",
        "summary": "本次周会讨论了 Q3 路线图，确认语音助手与 PDF 智能抽取为优先级最高的两项能力。",
        "summary_truncated": false,
        "tags": ["周会", "Q3规划", "路线图"],
        "updated_at": "2026-07-12T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

### 交互流程

- 进入资源列表页 -> 调用 `GET /api/v1/resources?page=1&limit=20` 加载首屏
- 卡片渲染：标题行（资源名 + 状态 Chip）-> `ResourceSummaryText`（2 行折叠）-> `TagChipRow`（横向滚动 Chip）
- 点击“展开” -> 摘要显示完整内容并切换为“收起”；点击“收起” -> 恢复 2 行折叠
- 点击任一标签 -> 将 `tag` 写入筛选状态，重新请求 `GET /api/v1/resources?tag=周会`，顶部出现筛选条
- 点击“清除筛选” -> 清空 `tag`，恢复全量列表
- 下拉刷新 / 上拉分页加载更多（复用 S1-6 骨架）

### 错误处理

- 摘要或标签字段缺失/为 null 时，卡片显示对应占位文案，不抛异常
- 列表请求 4xx/5xx -> 显示错误提示与重试按钮
- 筛选请求失败 -> 保持原列表，提示“筛选失败，请重试”
- 未登录（401） -> 路由守卫跳转登录页

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| S4-1/S4-2 抽取结果未落库 | summary/tags 为空 | 卡片对空值做占位处理，不阻塞渲染 |
| 标签数量多导致 Chip 溢出 | 移动端布局错乱 | 使用横向滚动 `SingleChildScrollView` + `Wrap` 降级 |
| 长摘要渲染性能差 | 列表滚动卡顿 | 折叠态仅渲染 2 行，展开按需渲染 |
| Web 端 Chip 横向滚动行为差异 | 体验不一致 | 统一封装 `TagChipRow`，Web 端验证滚动与点击事件 |

---

## Web 端适配

- 卡片布局使用 `LayoutBuilder` / `ConstrainedBox`，宽屏限制最大宽度并居中
- `TagChipRow` 使用 `SingleChildScrollView(scrollDirection: Axis.horizontal)`，Web 端鼠标可拖拽滚动并支持点击
- Chip 溢出时统一显示省略与横向滚动条，避免换行撑高卡片
- Web 端 Dio 请求受 CORS 限制，Gateway 需为 `/api/v1/resources` 配置允许 Flutter Web 域名跨域头
- 使用 `flutter test --platform chrome` 验证 Widget 渲染、Chip 滚动与标签过滤交互

---

## 备注

- 资源列表页为本次新建，复用 S1-6 任务中心的列表骨架（下拉刷新、分页、空/错误状态）
- 摘要截断阈值默认 2 行；如后端返回 `summary_truncated=true`，展开时需提示“仅展示摘要前 N 字，查看完整内容请进入详情”
- 标签过滤为单选（单标签筛选），多标签组合筛选为后续 Sprint 可选项
- 与 S2-7 内容查看页保持路由一致：点击卡片主体跳转 `/resources/:id/content`
