import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/data/datasources/remote/chat_event_parser.dart';
import 'package:mkc_client/domain/entities/message.dart';

void main() {
  group('ChatEventParser.parseEvent', () {
    test('parses chunk event', () {
      final json = jsonEncode({'message_id': 'm-1', 'delta': 'hello'});
      final event = ChatEventParser.parseEvent('event: chunk\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.type, 'chunk');
      expect(event.messageId, 'm-1');
      expect(event.delta, 'hello');
    });

    test('parses multi-line data event', () {
      final event = ChatEventParser.parseEvent(
        'event: chunk\ndata: {"message_id":"m-2",\ndata: "delta":"line1"}\n',
      );
      expect(event, isNotNull);
      expect(event!.type, 'chunk');
      expect(event.messageId, 'm-2');
      expect(event.delta, 'line1');
    });

    test('parses citation event', () {
      final json = jsonEncode({
        'index': 1,
        'chunk_id': 'chunk-1',
        'resource_id': 'r-1',
        'resource_name': 'Paper',
        'resource_type': 'pdf',
        'page': 12,
        'snippet': 'quoted text',
        'score': 0.95,
      });
      final event =
          ChatEventParser.parseEvent('event: citation\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.type, 'citation');
      expect(event.citation, isNotNull);
      expect(event.citation!.resourceId, 'r-1');
      expect(event.citation!.index, 1);
      expect(event.citation!.chunkId, 'chunk-1');
      expect(event.citation!.resourceName, 'Paper');
      expect(event.citation!.page, '12');
      expect(event.citation!.snippet, 'quoted text');
      expect(event.citation!.score, 0.95);
      expect(event.citation!.contentType, 'pdf');
    });

    test('parses audio citation timestamps from top-level fields', () {
      final json = jsonEncode({
        'resource_id': 'r-2',
        'resource_type': 'audio',
        'timestamp_start': 75.5,
        'timestamp_end': 90,
        'score': 0.88,
      });
      final event =
          ChatEventParser.parseEvent('event: citation\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.citation!.timestamp, const Duration(milliseconds: 75500));
      expect(event.citation!.timestampEnd, const Duration(seconds: 90));
      expect(event.citation!.contentType, 'audio');
    });

    test('skips citation event when resource_id is missing', () {
      final json = jsonEncode({
        'resource_name': 'Paper',
        'score': 0.95,
      });
      final event =
          ChatEventParser.parseEvent('event: citation\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.citation, isNull);
    });

    test('parses done event', () {
      final json = jsonEncode({'message_id': 'm-3'});
      final event = ChatEventParser.parseEvent('event: done\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.type, 'done');
      expect(event.messageId, 'm-3');
    });

    test('parses error event with code and message', () {
      final json = jsonEncode({
        'message_id': 'm-4',
        'error_code': 'UNAUTHORIZED',
        'message': 'session expired',
      });
      final event = ChatEventParser.parseEvent('event: error\ndata: $json\n');
      expect(event, isNotNull);
      expect(event!.type, 'error');
      expect(event.errorCode, 'UNAUTHORIZED');
      expect(event.errorMessage, 'session expired');
    });

    test('returns null for empty data', () {
      final event = ChatEventParser.parseEvent('event: chunk\n');
      expect(event, isNull);
    });

    test('returns null for invalid JSON data', () {
      final event = ChatEventParser.parseEvent(
        'event: chunk\ndata: not-json\n',
      );
      expect(event, isNull);
    });
  });

  group('ChatEventParser.parseEventData', () {
    test('parses event type and payload directly', () {
      final json = jsonEncode({'message_id': 'm-5', 'delta': 'hi'});
      final event = ChatEventParser.parseEventData('chunk', json);
      expect(event, isNotNull);
      expect(event!.type, 'chunk');
      expect(event.messageId, 'm-5');
      expect(event.delta, 'hi');
    });

    test('returns null for empty data', () {
      final event = ChatEventParser.parseEventData('chunk', '');
      expect(event, isNull);
    });
  });

  group('ChatEventParser.parseAssistantMessage', () {
    test('returns assistant message with defaults', () {
      final message = ChatEventParser.parseAssistantMessage({
        'message_id': 'm-6',
        'conversation_id': 'c-1',
        'content': 'answer',
        'created_at': 1700000000,
        'is_streaming': false,
      });
      expect(message.role, MessageRole.assistant);
      expect(message.id, 'm-6');
      expect(message.conversationId, 'c-1');
      expect(message.content, 'answer');
      expect(message.isStreaming, false);
    });

    test('uses current time when timestamp is missing', () {
      final message = ChatEventParser.parseAssistantMessage({
        'message_id': 'm-7',
      });
      expect(message.createdAt, isA<DateTime>());
    });
  });
}
