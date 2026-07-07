import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

void main() {
  test('Result.success carries data', () {
    const result = Result<int>.success(42);

    expect(
      result.when(success: (data) => data, failure: (_) => -1),
      equals(42),
    );
  });

  test('Result.failure carries error', () {
    const result = Result<int>.failure(NetworkException());

    expect(
      result.when(success: (_) => null, failure: (error) => error),
      isA<NetworkException>(),
    );
  });
}
