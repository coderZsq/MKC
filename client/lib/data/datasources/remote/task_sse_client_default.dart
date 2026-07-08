import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import '../../../domain/entities/task_event.dart';
import '../../../domain/repositories/token_provider.dart';
import 'task_sse_client.dart';

const int _maxReconnectAttempts = 5;
const int _fallbackPollIntervalSeconds = 5;

class TaskSseClientImpl implements TaskSseClient {
  TaskSseClientImpl({
    required String baseUrl,
    required TokenProvider tokenProvider,
  })  : _tokenProvider = tokenProvider,
        _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 30),
            responseType: ResponseType.stream,
          ),
        );

  final TokenProvider _tokenProvider;
  final Dio _dio;

  @override
  Stream<TaskEvent> subscribe(String taskId) {
    StreamSubscription<TaskEvent>? sseSub;
    Timer? pollTimer;
    final controller = StreamController<TaskEvent>(
      onCancel: () async {
        sseSub?.cancel();
        pollTimer?.cancel();
      },
    );

    void startPolling() {
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
              '/tasks/$taskId',
              options: Options(
                headers: token != null
                    ? <String, String>{'Authorization': 'Bearer $token'}
                    : null,
              ),
            );
            final data = response.data as Map<String, dynamic>?;
            if (data == null) return;
            final event = TaskEvent.fromJson(
              data,
              eventType: _eventTypeForStatus(data['status'] as String? ?? ''),
            );
            controller.add(event);
            if (_isTerminal(event.status)) {
              timer.cancel();
              await controller.close();
            }
          } catch (_) {
            // Ignore polling errors; the next tick will retry.
          }
        },
      );
    }

    late final void Function(int) attemptSse;
    attemptSse = (int attempt) async {
      if (attempt > _maxReconnectAttempts) {
        startPolling();
        return;
      }
      try {
        final token = await _tokenProvider.getAccessToken();
        final response = await _dio.get<ResponseBody>(
          '/tasks/$taskId/events',
          options: Options(
            headers: token != null
                ? <String, String>{'Authorization': 'Bearer $token'}
                : null,
            responseType: ResponseType.stream,
          ),
        );
        final body = response.data;
        if (body == null) {
          throw StateError('empty SSE response body');
        }
        sseSub = _parseSseStream(body.stream).listen(
          (event) {
            controller.add(event);
            if (_isTerminal(event.status) && !controller.isClosed) {
              controller.close();
            }
          },
          onError: (_) => attemptSse(attempt + 1),
          onDone: () {
            if (!controller.isClosed) {
              controller.close();
            }
          },
          cancelOnError: false,
        );
      } catch (_) {
        attemptSse(attempt + 1);
      }
    };

    attemptSse(0);

    return controller.stream;
  }

  Stream<TaskEvent> _parseSseStream(Stream<List<int>> stream) {
    return stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .transform(_sseEventTransformer());
  }

  static StreamTransformer<String, TaskEvent> _sseEventTransformer() {
    String eventType = 'message';
    final dataBuffer = StringBuffer();

    return StreamTransformer<String, TaskEvent>.fromHandlers(
      handleData: (line, sink) {
        if (line.isEmpty) {
          final data = dataBuffer.toString();
          if (data.isNotEmpty) {
            try {
              final json = jsonDecode(data) as Map<String, dynamic>;
              sink.add(TaskEvent.fromJson(json, eventType: eventType));
            } catch (_) {
              // Ignore malformed events.
            }
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
          try {
            final json = jsonDecode(data) as Map<String, dynamic>;
            sink.add(TaskEvent.fromJson(json, eventType: eventType));
          } catch (_) {
            // Ignore malformed events.
          }
        }
        sink.close();
      },
    );
  }

  static bool _isTerminal(String status) {
    return status == 'completed' || status == 'failed';
  }

  static String _eventTypeForStatus(String status) {
    return switch (status) {
      'completed' => 'done',
      'failed' => 'error',
      _ => 'status',
    };
  }
}
