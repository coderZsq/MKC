# PRD：[S1-4] 实现 Flutter 文件选择/上传页面

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  > 关联文档：[PRD_S1-3_file_upload_api.md](./PRD_S1-3_file_upload_api.md)、[TECH_S1-4_flutter_upload_page.md](../tech/TECH_S1-4_flutter_upload_page.md)

---

## 任务元信息

| 项 | 内容 |
|---|---|
| **任务卡编号** | S1-4 |
| **任务名称** | 实现 Flutter 文件选择/上传页面 |
| **所属史诗** | E2 资源管理 |
| **故事点** | 3 |
| **优先级** | Must |
| **依赖** | S1-2 Flutter 登录/注册、S1-3 文件上传 API |
| **目标 Sprint** | Sprint 1 |

---

## 描述

作为已登录用户，我需要从 iOS、Android 或 Web（Chrome）设备选择多媒体文件并上传到服务端，随后查看上传结果并进入任务中心跟踪处理进度。本任务在 Flutter 客户端实现跨平台文件选择、本地校验、上传进度展示、结果反馈与页面导航。

---

## 验收标准（AC）

- [ ] **AC-1** 提供 `UploadPage`，已登录用户可通过底部导航或首页入口进入
- [ ] **AC-2** 支持调用系统文件选择器（`file_picker`）选择单个文件
- [ ] **AC-3** 本地校验文件大小：Web ≤ 100 MB，移动端/桌面端 ≤ 500 MB；扩展名/MIME 在白名单内
- [ ] **AC-4** 上传过程中显示进度条（0-100%）与取消按钮
- [ ] **AC-5** 上传成功后展示 resource_id、文件名、任务类型，并提供“查看任务”入口
- [ ] **AC-6** 上传失败时显示明确错误：文件过大、格式不支持、网络异常、服务错误
- [ ] **AC-7** 上传接口调用携带 access_token，401 时自动触发刷新或跳转登录
- [ ] **AC-8** 使用 Riverpod 管理上传状态
- [ ] **AC-9** Widget 测试覆盖选择文件、上传成功、上传失败分支
- [ ] **AC-10** 上传流程在 Web（Chrome）端可正常运行：文件选择、bytes 上传、进度展示、结果反馈

---

## 推荐目录结构

```
client/lib/
├── data/
│   ├── datasources/
│   │   └── remote/
│   │       ├── auth_api.dart        # S1-2 已引入
│   │       └── file_api.dart        # /files/upload 封装
│   ├── models/
│   │   ├── upload_request_model.dart
│   │   └── upload_response_model.dart
│   └── repositories/
│       └── file_repository.dart
├── presentation/
│   ├── pages/
│   │   └── upload_page.dart
│   ├── providers/
│   │   └── upload_provider.dart
│   └── widgets/
│       └── upload_progress_bar.dart
└── shared/
    └── validators/
        └── file_validator.dart
```

---

## 核心依赖

| 依赖 | 版本 | 用途 |
|---|---|---|
| file_picker | ^8.0.5 | 系统文件选择 |
| dio | ^5.4.3 | multipart 上传 |
| flutter_riverpod | ^2.5.1 | 状态管理 |
| freezed | ^2.5.2 | 不可变模型 |

---

## 技术要点

### 文件选择

- 使用 `FilePicker.platform.pickFiles()`，Sprint 1 不限制文件类型，但 UI 给出推荐格式提示
- 平台适配：移动端/桌面端使用文件路径 + `MultipartFile.fromFile`；Web 端 `file_picker` 返回 `Uint8List` bytes，使用 `MultipartFile.fromBytes` 上传
- 统一封装为 `PickedFile` 对象（`path`、`bytes`、`name`、`size`、`extension`），上传层根据平台自动选择构建方式

### 本地校验

- 大小：≤ 500MB（`FilePickerResult.files.first.size`）
- 扩展名白名单：`mp3`, `wav`, `mp4`, `webm`, `pdf`, `txt`, `doc`, `docx`
- 校验失败立即提示，不上传

### 上传状态

- `UploadState` 包含：`idle`、`picking`、`validating`、`uploading(progress)`、`success(result)`、`failure(error)`
- 取消上传：调用 `CancelToken.cancel()`，UI 回到 idle

### 错误处理

- `NetworkException` → 网络异常
- 413 → 文件过大
- 415 → 不支持的文件类型
- 401 → 触发 token 刷新，失败后跳转登录
- 其他 → 服务繁忙

---

## 阻塞风险

| 风险 | 影响 | 应对 |
|---|---|---|
| Web 端 file_picker 只能返回 bytes，大文件会加载到浏览器内存 | OOM / 上传失败 | Web 端限制单次上传文件大小（建议 ≤ 100MB），并提示用户；大文件分片上传放到后续迭代 |
| 大文件上传导致内存占用高 | OOM | multipart 移动端使用文件路径而非 bytes；Web 端受浏览器内存限制，需控制文件大小并开启 dio onSendProgress |
| S1-3 API 未完成 | 无法真机联调 | 使用 mock FileRepository 先行开发 UI | 

---

## Web 端适配

- Web 端 `file_picker` 返回 `PlatformFile.bytes`，上传层统一封装为 `PickedFile`，根据 `bytes != null` 自动使用 `MultipartFile.fromBytes`。
- Web 端 Dio 上传受 CORS 限制，要求 S1-3 Gateway 配置允许 Flutter Web 域名的跨域头与 multipart 请求。
- Web 端上传进度通过 dio `onSendProgress` 计算，但浏览器上传进度粒度取决于浏览器实现，UI 进度条应兼容平滑动画。
- Web 端建议限制单次上传文件大小（如 ≤ 100MB），避免浏览器内存占用过高；移动端/桌面端维持 500MB 限制。
- Web 端 Widget/单元测试使用 `flutter test --platform chrome`；集成测试使用 ChromeDriver 选择本地测试文件。

---

## 备注

- 当前 Sprint 仅支持单次单文件上传；多文件与断点续传后续迭代
- 上传成功后自动跳转到 TaskCenterPage（S1-6）
- 如需支持 iOS 文件访问，需在 `Info.plist` 添加 `UIFileSharingEnabled` 与文档类型声明
