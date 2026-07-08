// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;

import 'package:dio/dio.dart';

import '../../../domain/entities/task_event.dart';
import '../../../domain/repositories/token_provider.dart';
import 'task_sse_client.dart';

const int _maxReconnectAttempts = 5;
const int _fallbackPollIntervalSeconds = 5;
const List<String> _eventNames = <String>[
  'progress',
  'status',
  'done',
  'error',
  'heartbeat',
];

class TaskSseClientImpl implements TaskSseClient {
  TaskSseClientImpl({
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
  Stream<TaskEvent> subscribe(String taskId) {
    html.EventSource? eventSource;
    Timer? pollTimer;
    final controller = StreamController<TaskEvent>(
      onCancel: () {
        eventSource?.close();
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

    void connect({int attempt = 0}) async {
      if (attempt > _maxReconnectAttempts) {
        eventSource?.close();
        startPolling();
        return;
      }

      final token = await _tokenProvider.getAccessToken();
      final uri = Uri.parse('$_baseUrl/tasks/$taskId/events').replace(
        queryParameters: token != null
            ? <String, String>{'token': token}
            : null,
      );

      eventSource = html.EventSource(uri.toString());

      for (final name in _eventNames) {
        eventSource!.addEventListener(
          name,
          (html.Event event) {
            final messageEvent = event as html.MessageEvent;
            final raw = messageEvent.data?.toString() ?? '';
            if (raw.isEmpty) return;
            try {
              final json = jsonDecode(raw) as Map<String, dynamic>;
              final taskEvent = TaskEvent.fromJson(json, eventType: name);
              controller.add(taskEvent);
              if (_isTerminal(taskEvent.status) && !controller.isClosed) {
                eventSource?.close();
                controller.close();
              }
            } catch (_) {
              // Ignore malformed events.
            }
          },
        );
      }

      eventSource!.onError.listen((_) {
        eventSource?.close();
        Timer(Duration(seconds: attempt + 1), () {
          if (!controller.isClosed) connect(attempt: attempt + 1);
        });
      });

      eventSource!.onOpen.listen((_) {
        // Reset reconnect counter on successful connection.
      });
    }

    connect();

    return controller.stream;
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
