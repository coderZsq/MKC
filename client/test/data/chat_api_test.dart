import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/api_client.dart';
import 'package:mkc_client/data/datasources/remote/chat_api.dart';
import 'package:mkc_client/domain/repositories/token_provider.dart';

class _FakeTokenProvider implements TokenProvider {
  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<bool> refreshAccessToken() async => false;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {}
}

class _MockAdapter implements HttpClientAdapter {
  _MockAdapter({required this.onFetch});

  final ResponseBody Function(RequestOptions options) onFetch;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return onFetch(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _jsonBody(Object body, {required int statusCode}) {
  final bytes = Uint8List.fromList(utf8.encode(jsonEncode(body)));
  return ResponseBody.fromBytes(
    bytes,
    statusCode,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

const _conversationJson = {
  'id': 'conv-1',
  'title': 'New chat',
  'resource_ids': <String>[],
  'model_config': null,
  'created_at': 1700000000,
  'updated_at': 1700000000,
};

const _messageJson = {
  'id': 'msg-1',
  'conversation_id': 'conv-1',
  'role': 'user',
  'content': 'Hello',
  'citations': <Map<String, dynamic>>[],
  'created_at': 1700000000,
};

void main() {
  group('ChatApi', () {
    late Dio dio;
    late ChatApi chatApi;

    setUp(() {
      dio = Dio(BaseOptions(baseUrl: 'http://localhost:8080'));
      final apiClient = ApiClient(
        baseUrl: 'http://localhost:8080',
        tokenProvider: _FakeTokenProvider(),
        dio: dio,
      );
      chatApi = ChatApi(client: apiClient);
    });

    test('listConversations fetches and parses conversation list', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/conversations'));
          expect(options.method, equals('GET'));
          return _jsonBody(
            {
              'success': true,
              'data': [_conversationJson],
              'error': null,
              'meta': null,
            },
            statusCode: 200,
          );
        },
      );

      final result = await chatApi.listConversations();
      result.when(
        success: (list) {
          expect(list, hasLength(1));
          expect(list.first.conversationId, 'conv-1');
        },
        failure: (_) => fail('expected success'),
      );
    });

    test('createConversation sends optional title and resource_ids', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/conversations'));
          expect(options.method, equals('POST'));
          expect(
            options.data,
            equals({'title': 'Project', 'resource_ids': ['res-1']}),
          );
          return _jsonBody(
            {
              'success': true,
              'data': _conversationJson,
              'error': null,
              'meta': null,
            },
            statusCode: 201,
          );
        },
      );

      final result = await chatApi.createConversation(
        title: 'Project',
        resourceIds: const ['res-1'],
      );
      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
    });

    test('createConversation omits empty optional fields', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.data, isNull);
          return _jsonBody(
            {
              'success': true,
              'data': _conversationJson,
              'error': null,
              'meta': null,
            },
            statusCode: 201,
          );
        },
      );

      final result = await chatApi.createConversation();
      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
    });

    test('loadMessages fetches paginated messages for a conversation', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/conversations/conv-1/messages'));
          expect(options.method, equals('GET'));
          expect(options.queryParameters, isEmpty);
          return _jsonBody(
            {
              'success': true,
              'data': {
                'items': [_messageJson],
                'total': 1,
                'page': 1,
                'limit': 20,
              },
              'error': null,
              'meta': null,
            },
            statusCode: 200,
          );
        },
      );

      final result = await chatApi.loadMessages('conv-1');
      result.when(
        success: (list) {
          expect(list, hasLength(1));
          expect(list.first.messageId, 'msg-1');
        },
        failure: (_) => fail('expected success'),
      );
    });

    test('loadMessages forwards page and limit query parameters', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/conversations/conv-1/messages'));
          expect(options.queryParameters, equals({'page': 2, 'limit': 10}));
          return _jsonBody(
            {
              'success': true,
              'data': {'items': [], 'total': 0, 'page': 2, 'limit': 10},
              'error': null,
              'meta': null,
            },
            statusCode: 200,
          );
        },
      );

      final result = await chatApi.loadMessages('conv-1', page: 2, limit: 10);
      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
    });

    test('deleteConversation calls DELETE endpoint', () async {
      dio.httpClientAdapter = _MockAdapter(
        onFetch: (options) {
          expect(options.path, equals('/conversations/conv-1'));
          expect(options.method, equals('DELETE'));
          return _jsonBody(
            {
              'success': true,
              'data': null,
              'error': null,
              'meta': null,
            },
            statusCode: 200,
          );
        },
      );

      final result = await chatApi.deleteConversation('conv-1');
      expect(
        result.when(success: (_) => true, failure: (_) => false),
        isTrue,
      );
    });
  });
}
