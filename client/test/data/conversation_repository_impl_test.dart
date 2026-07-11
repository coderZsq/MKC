import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/chat_api.dart';
import 'package:mkc_client/data/models/conversation_model.dart';
import 'package:mkc_client/data/models/message_model.dart';
import 'package:mkc_client/data/repositories/conversation_repository_impl.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

class _FakeChatApi implements ChatApi {
  Result<List<ConversationModel>>? nextListResult;
  Result<ConversationModel>? nextCreateResult;
  Result<void>? nextDeleteResult;
  String? lastCreateTitle;
  List<String>? lastCreateResourceIds;
  String? lastDeletedId;

  @override
  Future<Result<List<ConversationModel>>> listConversations() async {
    return nextListResult ?? const Result.success([]);
  }

  @override
  Future<Result<ConversationModel>> createConversation({
    String? title,
    List<String>? resourceIds,
  }) async {
    lastCreateTitle = title;
    lastCreateResourceIds = resourceIds;
    return nextCreateResult ?? Result.success(_defaultModel());
  }

  @override
  Future<Result<void>> deleteConversation(String conversationId) async {
    lastDeletedId = conversationId;
    return nextDeleteResult ?? const Result.success(null);
  }

  ConversationModel _defaultModel() => ConversationModel(
        conversationId: 'new',
        title: '',
        createdAt: DateTime.fromMillisecondsSinceEpoch(1700000000000),
        updatedAt: DateTime.fromMillisecondsSinceEpoch(1700000000000),
      );

  @override
  Future<Result<List<MessageModel>>> loadMessages(
    String conversationId, {
    int? page,
    int? limit,
  }) async {
    throw UnimplementedError();
  }
}

void main() {
  group('ConversationRepositoryImpl', () {
    late _FakeChatApi fakeApi;
    late ConversationRepositoryImpl repository;

    setUp(() {
      fakeApi = _FakeChatApi();
      repository = ConversationRepositoryImpl(chatApi: fakeApi);
    });

    test('listConversations maps models to domain entities', () async {
      fakeApi.nextListResult = Result.success([
        ConversationModel(
          conversationId: 'c1',
          title: 'One',
          createdAt: DateTime.fromMillisecondsSinceEpoch(1700000000000),
          updatedAt: DateTime.fromMillisecondsSinceEpoch(1700000001000),
        ),
      ]);

      final result = await repository.listConversations();
      result.when(
        success: (list) {
          expect(list, hasLength(1));
          expect(list.first.id, 'c1');
          expect(list.first.title, 'One');
        },
        failure: (_) => fail('expected success'),
      );
    });

    test('createConversation forwards title and resource ids', () async {
      fakeApi.nextCreateResult = Result.success(
        ConversationModel(
          conversationId: 'c2',
          title: 'Project',
          resourceIds: const ['res-1'],
          createdAt: DateTime.fromMillisecondsSinceEpoch(1700000000000),
          updatedAt: DateTime.fromMillisecondsSinceEpoch(1700000000000),
        ),
      );

      final result = await repository.createConversation(
        title: 'Project',
        resourceIds: const ['res-1'],
      );
      expect(result.when(success: (_) => true, failure: (_) => false), isTrue);
      expect(fakeApi.lastCreateTitle, 'Project');
      expect(fakeApi.lastCreateResourceIds, ['res-1']);
    });

    test('deleteConversation forwards conversation id', () async {
      fakeApi.nextDeleteResult = const Result.success(null);

      final result = await repository.deleteConversation('c1');
      expect(result.when(success: (_) => true, failure: (_) => false), isTrue);
      expect(fakeApi.lastDeletedId, 'c1');
    });

    test('propagates failure from api', () async {
      fakeApi.nextListResult = const Result.failure(NetworkException());

      final result = await repository.listConversations();
      expect(result.when(success: (_) => false, failure: (_) => true), isTrue);
    });
  });
}
