import 'errors/app_exception.dart';

/// Result type representing either a success value or an application error.
sealed class Result<T> {
  const Result();

  const factory Result.success(T data) = Success<T>;
  const factory Result.failure(AppException error) = Failure<T>;

  R when<R>({
    required R Function(T data) success,
    required R Function(AppException error) failure,
  });
}

class Success<T> extends Result<T> {
  const Success(this.data);

  final T data;

  @override
  R when<R>({
    required R Function(T data) success,
    required R Function(AppException error) failure,
  }) =>
      success(data);
}

class Failure<T> extends Result<T> {
  const Failure(this.error);

  final AppException error;

  @override
  R when<R>({
    required R Function(T data) success,
    required R Function(AppException error) failure,
  }) =>
      failure(error);
}
