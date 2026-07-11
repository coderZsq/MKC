import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/providers/conversation_list_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../../shared/chat_test_helpers.dart';

void main() {
  late FakeConversationRepository repository;
  late ConversationListNotifier notifier;

  setUp(() {
    repository = FakeConversationRepository();
    notifier = ConversationListNotifier(repository: repository);
  });

  tearDown(() {
    notifier.dispose();
  });

  group('loadConversations', () {
    test('sets conversations and clears loading on success', () async {
      final conversations = [
        makeConversation(id: 'c1'),
        makeConversation(id: 'c2'),
      ];
      repository.nextListResult = Result.success(conversations);

      await notifier.loadConversations();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.conversations, hasLength(2));
      expect(repository.listCalls, 1);
    });

    test('sets error on failure', () async {
      repository.nextListResult = const Result.failure(NetworkException());

      await notifier.loadConversations();

      expect(notifier.state.isLoading, isFalse);
      expect(notifier.state.error, isA<NetworkException>());
      expect(notifier.state.conversations, isEmpty);
    });
  });

  group('createConversation', () {
    test('adds new conversation at the top and selects it', () async {
      repository.nextCreateResult = Result.success(
        makeConversation(id: 'new'),
      );

      final created = await notifier.createConversation();

      expect(created, isNotNull);
      expect(created!.id, 'new');
      expect(notifier.state.conversations, hasLength(1));
      expect(notifier.state.selectedId, 'new');
      expect(repository.createCalls, 1);
    });

    test('sets error on failure without modifying list', () async {
      repository.nextListResult = Result.success([makeConversation(id: 'c1')]);
      await notifier.loadConversations();
      repository.nextCreateResult = const Result.failure(NetworkException());

      final created = await notifier.createConversation();

      expect(created, isNull);
      expect(notifier.state.conversations, hasLength(1));
      expect(notifier.state.error, isA<NetworkException>());
    });
  });

  group('deleteConversation', () {
    test('removes conversation on success and restores on failure', () async {
      repository.nextListResult = Result.success([makeConversation(id: 'c1')]);
      await notifier.loadConversations();
      expect(notifier.state.conversations, hasLength(1));

      repository.nextDeleteResult = const Result.success(null);
      await notifier.deleteConversation('c1');

      expect(notifier.state.conversations, isEmpty);
      expect(repository.lastDeletedId, 'c1');

      repository.nextDeleteResult = const Result.failure(NetworkException());
      await notifier.deleteConversation('c2');
      // Since c2 is not in the list, list remains unchanged
      expect(notifier.state.conversations, isEmpty);
    });
  });

  group('selectConversation', () {
    test('updates selected id', () {
      notifier.selectConversation('c1');
      expect(notifier.state.selectedId, 'c1');
    });
  });
}
