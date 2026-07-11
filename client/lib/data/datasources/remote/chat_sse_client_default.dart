import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

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
  })  : _tokenProvider = tokenProvider,
        _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 30),
            responseType: ResponseType.stream,
            validateStatus: (status) => status != null && status < 500,
          ),
        );

  final TokenProvider _tokenProvider;
  final Dio _dio;

  @override
  Stream<ChatEvent> ask(String conversationId, String question) {
    StreamSubscription<ChatEvent>? sseSub;
    Timer? pollTimer;
    final cancelToken = CancelToken();
    final controller = StreamController<ChatEvent>();
    controller.onCancel = () async {
      sseSub?.cancel();
      pollTimer?.cancel();
      if (!cancelToken.isCancelled) {
        cancelToken.cancel();
      }
      if (!controller.isClosed) {
        await controller.close();
      }
    };

    void startPolling(String messageId) {
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
            final data = response.data as List<dynamic>?;
            if (data == null || data.isEmpty) return;
            final lastMessage = _parseLastAssistantMessage(data);
            if (lastMessage != null) {
              controller.add(
                ChatEvent(
                  type: 'chunk',
                  messageId: messageId.isEmpty ? lastMessage.id : messageId,
                  conversationId: conversationId,
                  delta: lastMessage.content,
                ),
              );
              if (!lastMessage.isStreaming) {
                controller.add(
                  ChatEvent(
                    type: 'done',
                    messageId: messageId.isEmpty ? lastMessage.id : messageId,
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
    }

    late final void Function(int) attemptSse;
    attemptSse = (int attempt) async {
      if (controller.isClosed) return;
      if (attempt > _maxReconnectAttempts) {
        startPolling('');
        return;
      }
      try {
        final token = await _tokenProvider.getAccessToken();
        final response = await _dio.post<ResponseBody>(
          '/conversations/$conversationId/ask',
          data: <String, dynamic>{'question': question},
          options: Options(
            headers: token != null
                ? <String, String>{'Authorization': 'Bearer $token'}
                : null,
            responseType: ResponseType.stream,
          ),
          cancelToken: cancelToken,
        );
        if (response.statusCode == 401 || response.statusCode == 403) {
          controller.add(
            ChatEvent(
              type: 'error',
              messageId: '',
              conversationId: conversationId,
              errorCode: 'UNAUTHORIZED',
              errorMessage: 'Authentication failed',
            ),
          );
          await controller.close();
          return;
        }
        if (response.statusCode != 200 || response.data == null) {
          throw StateError('SSE request failed: ${response.statusCode}');
        }
        sseSub = _parseSseStream(response.data!.stream).listen(
          (event) {
            controller.add(event);
            if (event.isTerminal && !controller.isClosed) {
              controller.close();
            }
          },
          onError: (Object e) {
            if (e is DioException && e.type == DioExceptionType.cancel) {
              if (!controller.isClosed) controller.close();
              return;
            }
            if (!controller.isClosed) attemptSse(attempt + 1);
          },
          onDone: () {
            if (!controller.isClosed) {
              controller.close();
            }
          },
          cancelOnError: false,
        );
      } catch (e) {
        if (e is DioException && e.type == DioExceptionType.cancel) {
          if (!controller.isClosed) controller.close();
          return;
        }
        if (!controller.isClosed) {
          await Future.delayed(Duration(seconds: attempt + 1));
          if (!controller.isClosed) attemptSse(attempt + 1);
        }
      }
    };

    attemptSse(0);

    return controller.stream;
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

  Stream<ChatEvent> _parseSseStream(Stream<List<int>> stream) {
    return stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .transform(_sseEventTransformer());
  }

  static StreamTransformer<String, ChatEvent> _sseEventTransformer() {
    String eventType = 'message';
    final dataBuffer = StringBuffer();

    return StreamTransformer<String, ChatEvent>.fromHandlers(
      handleData: (line, sink) {
        if (line.isEmpty) {
          final data = dataBuffer.toString();
          if (data.isNotEmpty) {
            final event = ChatEventParser.parseEventData(eventType, data);
            if (event != null) sink.add(event);
          }
          eventType = 'message';
          dataBuffer.clear();
          return;
        }

        if (line.startsWith('event:')) {
          eventType = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          if (dataBuffer.isNotEmpty) {
            dataBuffer.write('\n');
          }
          dataBuffer.write(line.substring(5).trim());
        }
      },
      handleDone: (sink) {
        final data = dataBuffer.toString();
        if (data.isNotEmpty) {
          final event = ChatEventParser.parseEventData(eventType, data);
          if (event != null) sink.add(event);
        }
        sink.close();
      },
    );
  }
}
