// ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:async';
import 'dart:convert';
import 'dart:js_interop';

import 'package:dio/dio.dart';
import 'package:web/web.dart' as web;

import '../../../domain/entities/chat_event.dart';
import '../../../domain/entities/message.dart';
import '../../../domain/repositories/token_provider.dart';
import 'chat_event_parser.dart';
import 'chat_sse_client.dart';

const int _maxReconnectAttempts = 5;
const int _fallbackPollIntervalSeconds = 5;

class ChatSseClientImpl implements ChatSseClient {
  ChatSseClientImpl({
    required String baseUrl,
    required TokenProvider tokenProvider,
  })  : _baseUrl = baseUrl,
        _tokenProvider = tokenProvider,
        _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 30),
          ),
        );

  final String _baseUrl;
  final TokenProvider _tokenProvider;
  final Dio _dio;

  @override
  Stream<ChatEvent> ask(String conversationId, String question) {
    final controller = StreamController<ChatEvent>();
    _startStream(controller, conversationId, question, attempt: 0);
    return controller.stream;
  }

  Future<void> _startStream(
    StreamController<ChatEvent> controller,
    String conversationId,
    String question, {
    required int attempt,
  }) async {
    if (attempt > _maxReconnectAttempts) {
      _startPolling(controller, conversationId);
      return;
    }

    try {
      final token = await _tokenProvider.getAccessToken();
      final uri = Uri.parse('$_baseUrl/conversations/$conversationId/ask');

      final abortController = web.AbortController();
      controller.onCancel = () async {
        abortController.abort();
        if (!controller.isClosed) {
          await controller.close();
        }
      };

      final headers = web.Headers();
      headers.append('Content-Type', 'application/json');
      if (token != null && token.isNotEmpty) {
        headers.append('Authorization', 'Bearer $token');
      }

      final init = web.RequestInit(
        method: 'POST',
        headers: headers,
        body: jsonEncode(<String, dynamic>{'question': question}).toJS,
        signal: abortController.signal,
      );

      final response = await web.window.fetch(uri.toString().toJS, init).toDart;
      if (response.status == 401 || response.status == 403) {
        _addError(
          controller,
          conversationId,
          'UNAUTHORIZED',
          'Authentication failed',
        );
        await controller.close();
        return;
      }
      if (!response.ok) {
        _addError(
          controller,
          conversationId,
          'HTTP_${response.status}',
          'SSE request failed: ${response.status}',
        );
        await controller.close();
        return;
      }

      final reader =
          response.body?.getReader() as web.ReadableStreamDefaultReader?;
      if (reader == null) {
        throw StateError('response body stream is null');
      }

      final buffer = StringBuffer();
      final decoder = web.TextDecoder('utf-8');
      while (!controller.isClosed) {
        final result = await reader.read().toDart;
        if (result.done) {
          final flushed = decoder.decode();
          buffer.write(flushed);
          _flushBuffer(buffer, controller);
          if (!controller.isClosed) {
            controller.close();
          }
          break;
        }
        final value = result.value;
        if (value == null) continue;
        final text = decoder.decode(
          value as JSObject,
          web.TextDecodeOptions(stream: true),
        );
        buffer.write(text);
        _parseBuffer(buffer, controller);
      }
    } catch (_) {
      if (!controller.isClosed) {
        Future.delayed(Duration(seconds: attempt + 1), () {
          if (!controller.isClosed) {
            _startStream(
              controller,
              conversationId,
              question,
              attempt: attempt + 1,
            );
          }
        });
      }
    }
  }

  void _startPolling(
      StreamController<ChatEvent> controller, String conversationId) {
    Timer? pollTimer;
    pollTimer = Timer.periodic(
      const Duration(seconds: _fallbackPollIntervalSeconds),
      (timer) async {
        if (controller.isClosed) {
          timer.cancel();
          return;
        }
        try {
          final token = await _tokenProvider.getAccessToken();
          final response = await _dio.get<dynamic>(
            '/conversations/$conversationId/messages',
            options: Options(
              headers: token != null
                  ? <String, String>{'Authorization': 'Bearer $token'}
                  : null,
            ),
          );
          if (response.statusCode != 200) return;
          final data = _messageItems(response.data);
          if (data == null || data.isEmpty) return;
          final lastMessage = _parseLastAssistantMessage(data);
          if (lastMessage != null) {
            controller.add(
              ChatEvent(
                type: 'chunk',
                messageId: lastMessage.id,
                conversationId: conversationId,
                delta: lastMessage.content,
              ),
            );
            if (!lastMessage.isStreaming) {
              controller.add(
                ChatEvent(
                  type: 'done',
                  messageId: lastMessage.id,
                  conversationId: conversationId,
                ),
              );
              timer.cancel();
              await controller.close();
            }
          }
        } catch (_) {
          // Ignore polling errors; the next tick will retry.
        }
      },
    );
    controller.onCancel = () async {
      pollTimer?.cancel();
      if (!controller.isClosed) {
        await controller.close();
      }
    };
  }

  Message? _parseLastAssistantMessage(List<dynamic> data) {
    for (final item in data.reversed) {
      final raw = item as Map<String, dynamic>?;
      if (raw == null) continue;
      final role = raw['role'] as String? ?? 'user';
      if (role == 'assistant') {
        return ChatEventParser.parseAssistantMessage(raw);
      }
    }
    return null;
  }

  List<dynamic>? _messageItems(dynamic data) {
    if (data is List<dynamic>) return data;
    if (data is Map<String, dynamic>) {
      final envelopeData = data['data'];
      if (envelopeData is Map<String, dynamic>) {
        final items = envelopeData['items'];
        if (items is List<dynamic>) return items;
      }
      if (envelopeData is List<dynamic>) return envelopeData;
    }
    return null;
  }

  void _addError(
    StreamController<ChatEvent> controller,
    String conversationId,
    String code,
    String message,
  ) {
    if (controller.isClosed) return;
    controller.add(
      ChatEvent(
        type: 'error',
        messageId: '',
        conversationId: conversationId,
        errorCode: code,
        errorMessage: message,
      ),
    );
  }

  void _parseBuffer(StringBuffer buffer, StreamController<ChatEvent> sink) {
    final text = buffer.toString();
    final events = <String>[];
    final bufferText = StringBuffer();

    var i = 0;
    while (i < text.length - 1) {
      if (text[i] == '\n' && text[i + 1] == '\n') {
        final event = bufferText.toString();
        if (event.isNotEmpty) {
          events.add(event);
        }
        bufferText.clear();
        i += 2;
      } else {
        bufferText.write(text[i]);
        i++;
      }
    }
    if (text.isNotEmpty) {
      bufferText.write(text[text.length - 1]);
    }
    buffer.clear();
    buffer.write(bufferText.toString());

    for (final event in events) {
      _flushEvent(event, sink);
    }
  }

  void _flushBuffer(StringBuffer buffer, StreamController<ChatEvent> sink) {
    final event = buffer.toString().trim();
    if (event.isNotEmpty) {
      _flushEvent(event, sink);
    }
    buffer.clear();
  }

  void _flushEvent(String event, StreamController<ChatEvent> sink) {
    final parsed = ChatEventParser.parseEvent(event);
    if (parsed != null) {
      sink.add(parsed);
    }
  }
}
