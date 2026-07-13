import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/resource_api.dart';
import 'package:mkc_client/data/models/resource_model.dart';
import 'package:mkc_client/data/repositories/resource_repository.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

class _FakeResourceApi extends ResourceApi {
  _FakeResourceApi() : super(client: _StubApiClient());

  String? lastTag;
  int? lastPage;
  int? lastLimit;
  Result<List<ResourceModel>> nextResult = Result.success([
    ResourceModel(
      resourceId: 'res-1',
      name: 'report.pdf',
      type: 'pdf_parse',
      status: 'completed',
      summary: '摘要',
      tags: const ['机器学习'],
      updatedAt: DateTime(2026),
    ),
  ]);

  @override
  Future<Result<List<ResourceModel>>> list({
    required int page,
    required int limit,
    String? tag,
  }) async {
    lastPage = page;
    lastLimit = limit;
    lastTag = tag;
    return nextResult;
  }
}

class _StubApiClient extends ApiClient {
  _StubApiClient()
      : super(baseUrl: 'http://localhost', tokenProvider: _StubTokenProvider());
}

class _StubTokenProvider implements TokenProvider {
  @override
  Future<void> clearTokens() async {}

  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {}
}

void main() {
  test('fetchResources maps models to entities', () async {
    final api = _FakeResourceApi();
    final repo = ResourceRepositoryImpl(api: api);

    final result = await repo.fetchResources(page: 1, limit: 20, tag: ' 机器学习 ');

    result.when(
      success: (resources) {
        expect(resources.single.summary, '摘要');
        expect(resources.single.tags, ['机器学习']);
      },
      failure: (error) => fail(error.message),
    );
    expect(api.lastTag, '机器学习');
  });

  test('rejects invalid tags before API call', () async {
    final api = _FakeResourceApi();
    final repo = ResourceRepositoryImpl(api: api);

    final empty = await repo.fetchResources(page: 1, limit: 20, tag: ' ');
    final long = await repo.fetchResources(
      page: 1,
      limit: 20,
      tag: 'abcdefghijklmnopqrstuvwxyz1234567',
    );

    expect(empty, isA<Failure<List>>());
    expect(long, isA<Failure<List>>());
    empty.when(
        success: (_) {},
        failure: (error) => expect(error, isA<ValidationException>()));
    expect(api.lastTag, isNull);
  });
}
