import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/datasources/remote/file_api.dart';
import 'app_provider.dart';
import '../../data/models/upload_response_model.dart';
import '../../data/repositories/file_repository.dart';
import '../../domain/entities/picked_file.dart';
import '../../domain/services/file_picker_service.dart';
import '../../shared/errors/app_exception.dart';
import '../../shared/errors/upload_error_mapper.dart';
import '../../shared/result.dart';
import '../../shared/validators/file_validator.dart';

/// Current status of the upload flow.
enum UploadStatus {
  initial,
  picking,
  validating,
  ready,
  uploading,
  success,
  failure,
  cancelled,
}

/// UI state for the upload page.
class UploadState {
  const UploadState({
    this.status = UploadStatus.initial,
    this.selectedFile,
    this.progress = 0,
    this.response,
    this.error,
  });

  final UploadStatus status;
  final PickedFile? selectedFile;
  final int progress;
  final UploadResponseModel? response;
  final AppException? error;

  bool get isPicking => status == UploadStatus.picking;
  bool get isUploading => status == UploadStatus.uploading;
  bool get canUpload => status == UploadStatus.ready;
  bool get hasError => status == UploadStatus.failure;
  bool get isSuccess => status == UploadStatus.success;
  bool get isCancelled => status == UploadStatus.cancelled;

  String? get errorMessage => error == null ? null : mapUploadErrorToMessage(error);

  UploadState copyWith({
    UploadStatus? status,
    PickedFile? selectedFile,
    int? progress,
    UploadResponseModel? response,
    AppException? error,
  }) {
    return UploadState(
      status: status ?? this.status,
      selectedFile: selectedFile ?? this.selectedFile,
      progress: progress ?? this.progress,
      response: response ?? this.response,
      error: error,
    );
  }
}

/// Manages file selection, validation and upload state.
class UploadNotifier extends StateNotifier<UploadState> {
  UploadNotifier({
    required FilePickerService picker,
    required FileRepository repository,
  })  : _picker = picker,
        _repository = repository,
        super(const UploadState());

  final FilePickerService _picker;
  final FileRepository _repository;
  CancelToken? _cancelToken;

  Future<void> pickFile() async {
    state = state.copyWith(status: UploadStatus.picking, error: null, response: null);
    final pickedFile = await _picker.pickSingleFile();
    if (pickedFile == null) {
      state = state.copyWith(status: UploadStatus.initial);
      return;
    }

    state = state.copyWith(status: UploadStatus.validating, selectedFile: pickedFile);
    final validationError = validatePickedFile(
      size: pickedFile.size,
      extension: pickedFile.extension,
      isWeb: kIsWeb,
    );

    if (validationError != null) {
      state = state.copyWith(status: UploadStatus.failure, error: validationError);
      return;
    }

    state = state.copyWith(status: UploadStatus.ready, error: null);
  }

  Future<void> upload() async {
    final file = state.selectedFile;
    if (file == null) return;

    _cancelToken?.cancel();
    _cancelToken = CancelToken();

    state = state.copyWith(status: UploadStatus.uploading, progress: 0, error: null);

    final Result<UploadResponseModel> result = await _repository.uploadFile(
      file: file,
      cancelToken: _cancelToken!,
      onProgress: (sent, total) {
        if (total <= 0) return;
        state = state.copyWith(progress: ((sent / total) * 100).round());
      },
    );

    state = result.when<UploadState>(
      success: (UploadResponseModel response) => state.copyWith(
        status: UploadStatus.success,
        response: response,
        progress: 100,
      ),
      failure: (error) {
        if (error is CancelledUploadException) {
          return state.copyWith(status: UploadStatus.cancelled, progress: 0);
        }
        return state.copyWith(status: UploadStatus.failure, error: error);
      },
    );
  }

  void cancel() {
    _cancelToken?.cancel();
  }

  void clear() {
    _cancelToken?.cancel();
    _cancelToken = null;
    state = const UploadState();
  }

  @override
  void dispose() {
    _cancelToken?.cancel();
    super.dispose();
  }
}

final filePickerServiceProvider = Provider<FilePickerService>((ref) {
  return FilePickerServiceImpl();
});

final fileRepositoryProvider = Provider<FileRepository>((ref) {
  final api = FileApi(client: ref.watch(apiClientProvider));
  return FileRepository(api: api);
});

final uploadNotifierProvider =
    StateNotifierProvider.autoDispose<UploadNotifier, UploadState>((ref) {
  return UploadNotifier(
    picker: ref.watch(filePickerServiceProvider),
    repository: ref.watch(fileRepositoryProvider),
  );
});

