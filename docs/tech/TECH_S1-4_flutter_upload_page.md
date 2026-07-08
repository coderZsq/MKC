# 技术文档：[S1-4] Flutter 文件选择/上传页面设计

> 版本：v1.0  
> 日期：2026-07-08  
> 作者：朱双泉  
> 级别：移动端/Web 端工程师  
> 关联 PRD：[PRD_S1-4_flutter_upload_page.md](../prd/PRD_S1-4_flutter_upload_page.md)

---

## 1. 文档目标

定义 Flutter 客户端文件上传模块的 UI 结构、数据模型、状态流转、网络层封装与测试方案，为 S1-4 编码提供可直接落地的蓝图。

---

## 2. 技术栈

- Flutter 3.22+
- Dart 3.4+
- file_picker 8.0
- dio 5.4
- flutter_riverpod 2.5
- freezed 2.5
- http_parser (for `MediaType`)

---

## 3. 数据模型

### 3.1 上传响应模型

```dart
@freezed
class UploadResponseModel with _$UploadResponseModel {
  const factory UploadResponseModel({
    @JsonKey(name: 'resource_id') required String resourceId,
    @JsonKey(name: 'task_id') required String taskId,
    required String name,
    required String type,
    required String status,
    @JsonKey(name: 'size_bytes') required int sizeBytes,
    @JsonKey(name: 'mime_type') String? mimeType,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _UploadResponseModel;

  factory UploadResponseModel.fromJson(Map<String, dynamic> json) =>
      _$UploadResponseModelFromJson(json);
}
```

### 3.2 上传状态

```dart
@freezed
class UploadState with _$UploadState {
  const factory UploadState.idle() = _Idle;
  const factory UploadState.picking() = _Picking;
  const factory UploadState.validating() = _Validating;
  const factory UploadState.uploading({required double progress}) = _Uploading;
  const factory UploadState.success(UploadResponseModel result) = _Success;
  const factory UploadState.failure(AppException error) = _Failure;
}
```

### 3.3 跨平台文件对象

```dart
import 'dart:typed_data';

class PickedFile {
  const PickedFile({
    this.path,
    this.bytes,
    required this.name,
    required this.size,
    this.extension,
  });

  final String? path;
  final Uint8List? bytes;
  final String name;
  final int size;
  final String? extension;
}
```

- 移动端/桌面端：`path` 有值，`bytes` 为 null。
- Web 端：`bytes` 有值，`path` 可能为 null 或浏览器伪造路径，代码以 `bytes != null` 优先。

---

## 4. 网络层

### 4.1 FileApi

```dart
class FileApi {
  FileApi({required Dio dio}) : _dio = dio;

  final Dio _dio;

  Future<Result<UploadResponseModel>> upload({
    required PickedFile file,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) async {
    final multipartFile = await _toMultipartFile(file);
    final formData = FormData.fromMap({'file': multipartFile});

    try {
      final response = await _dio.post<dynamic>(
        '/files/upload',
        data: formData,
        cancelToken: cancelToken,
        onSendProgress: onProgress,
      );
      final body = response.data as Map<String, dynamic>;
      return Result.success(
        UploadResponseModel.fromJson(body['data'] as Map<String, dynamic>),
      );
    } on DioException catch (e) {
      return Result.failure(_mapDioException(e));
    }
  }

  Future<MultipartFile> _toMultipartFile(PickedFile file) async {
    if (file.bytes case final bytes?) {
      return MultipartFile.fromBytes(
        bytes,
        filename: file.name,
        contentType: _mediaTypeFromExtension(file.extension),
      );
    }
    if (file.path case final path?) {
      return MultipartFile.fromFile(
        path,
        filename: file.name,
        contentType: _mediaTypeFromExtension(file.extension),
      );
    }
    throw ArgumentError('PickedFile must provide either path or bytes');
  }

  MediaType? _mediaTypeFromExtension(String? extension) {
    final mime = _mimeFromExtension(extension);
    return mime == null ? null : MediaType.parse(mime);
  }
}
```

### 4.2 扩展名与 MIME 映射

```dart
const _allowedExtensions = {
  'mp3', 'wav', 'mp4', 'webm', 'pdf', 'txt', 'doc', 'docx',
};

String? _mimeFromExtension(String? extension) {
  return switch (extension?.toLowerCase()) {
    'mp3' => 'audio/mpeg',
    'wav' => 'audio/wav',
    'mp4' => 'video/mp4',
    'webm' => 'video/webm',
    'pdf' => 'application/pdf',
    'txt' => 'text/plain',
    'doc' => 'application/msword',
    'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    _ => null,
  };
}
```

### 4.3 FileRepository

```dart
class FileRepository {
  FileRepository({required FileApi api}) : _api = api;

  final FileApi _api;

  Future<Result<UploadResponseModel>> uploadFile({
    required PickedFile file,
    required CancelToken cancelToken,
    required void Function(int sent, int total) onProgress,
  }) async {
    return _api.upload(
      file: file,
      cancelToken: cancelToken,
      onProgress: onProgress,
    );
  }
}
```

---

## 5. 状态管理

```dart
import 'package:flutter/foundation.dart';
import 'package:file_picker/file_picker.dart';

class UploadNotifier extends StateNotifier<UploadState> {
  UploadNotifier({required FileRepository repo}) : _repo = repo, super(const UploadState.idle());

  final FileRepository _repo;
  CancelToken? _cancelToken;

  Future<void> pickAndUpload() async {
    state = const UploadState.picking();
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      withData: kIsWeb,
      withReadStream: !kIsWeb,
    );

    if (result == null || result.files.isEmpty) {
      state = const UploadState.idle();
      return;
    }

    final picked = result.files.first;
    state = const UploadState.validating();

    final validation = _validate(picked);
    if (validation != null) {
      state = UploadState.failure(validation);
      return;
    }

    _cancelToken = CancelToken();
    state = const UploadState.uploading(progress: 0);

    final pickedFile = PickedFile(
      path: kIsWeb ? null : picked.path,
      bytes: kIsWeb ? picked.bytes : null,
      name: picked.name,
      size: picked.size,
      extension: picked.extension?.toLowerCase(),
    );

    final uploadResult = await _repo.uploadFile(
      file: pickedFile,
      cancelToken: _cancelToken!,
      onProgress: (sent, total) {
        if (total <= 0) return;
        state = UploadState.uploading(progress: sent / total);
      },
    );

    state = uploadResult.fold(
      (data) => UploadState.success(data),
      (err) => UploadState.failure(err),
    );
  }

  void cancel() {
    _cancelToken?.cancel('user cancelled');
    state = const UploadState.idle();
  }

  void reset() => state = const UploadState.idle();

  AppException? _validate(PlatformFile file) {
    final maxSize = kIsWeb ? 100 * 1024 * 1024 : 500 * 1024 * 1024;
    if (file.size > maxSize) {
      return const ValidationException('文件超过当前平台大小限制');
    }
    if (!_allowedExtensions.contains(file.extension?.toLowerCase())) {
      return const ValidationException('不支持的文件类型');
    }
    return null;
  }
}
```

---

## 6. UI 页面

### 6.1 UploadPage

- 顶部标题“上传文件”
- 中央区域：
  - idle：上传图标 + “选择文件”按钮 + 支持的格式提示
  - picking：loading
  - uploading：`UploadProgressBar` + 取消按钮
  - success：文件信息卡片 + “查看任务”按钮
  - failure：错误图标 + 错误文案 + “重试”按钮
- 底部：文件大小/格式限制说明

### 6.2 UploadProgressBar

```dart
class UploadProgressBar extends StatelessWidget {
  const UploadProgressBar({required this.progress, super.key});

  final double progress;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        LinearProgressIndicator(value: progress),
        Text('${(progress * 100).toStringAsFixed(0)}%'),
      ],
    );
  }
}
```

---

## 7. 错误映射

| 场景 | 异常/状态码 | 显示文案 |
|---|---|---|
| 文件超过平台限制 | ValidationException | 文件超过当前平台大小限制（Web ≤100MB，移动端 ≤500MB） |
| 扩展名不支持 | ValidationException | 不支持的文件类型 |
| 网络断开 | DioExceptionType.connectionError | 网络异常，请检查连接 |
| 413 | ServerException | 文件过大，请重新选择 |
| 415 | ServerException | 服务器不支持该文件类型 |
| 401 | UnauthorizedException | 登录已过期，请重新登录 |
| 其他 | ServerException | 上传失败，请稍后重试 |

---

## 8. 测试策略

- **单元测试**：`FileValidator`、`_mimeFromExtension`、`_toMultipartFile` 路径/bytes 分支、状态转换
- **Widget 测试**：点击选择、校验失败、上传成功、取消上传；使用 `flutter test --platform chrome` 验证 Web 渲染
- **集成测试**：真实选择文件 → 调用 S1-3 API → 跳转任务中心（Web 端使用 ChromeDriver）

---

## 9. Web 端适配要点

- `FilePicker.platform.pickFiles(withData: kIsWeb)` 保证 Web 端可读取 bytes，移动端不一次性加载到内存。
- 统一 `PickedFile` 对象：移动端 `path` 有值，Web 端 `bytes` 有值；上传层按优先级使用 `fromBytes` → `fromFile`。
- Web 端 Dio 上传受浏览器 CORS 限制，要求 S1-3 Gateway 配置允许 Flutter Web 启动地址的跨域头（`Access-Control-Allow-Origin` / `Access-Control-Allow-Headers` / `Access-Control-Allow-Credentials`）。
- Web 端单文件大小建议 ≤100MB，避免浏览器内存占用过高；移动端维持 500MB。
- 单元/Widget 测试使用 `flutter test --platform chrome`；集成测试使用 ChromeDriver 选择本地测试文件。

---

## 10. 检查清单

- [ ] `UploadPage` 页面实现
- [ ] `FilePicker` 调用与跨平台文件读取（path / bytes）
- [ ] 文件大小/扩展名本地校验（Web ≤100MB，移动端 ≤500MB）
- [ ] `PickedFile` 跨平台模型封装
- [ ] `FileApi` multipart 上传（fromFile / fromBytes）与进度回调
- [ ] `UploadNotifier` 状态管理
- [ ] 取消上传功能
- [ ] 成功/失败 UI 与错误文案
- [ ] Widget 测试与集成测试（含 Web 平台验证）
- [ ] `flutter analyze` 0 issues
