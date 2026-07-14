import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../domain/entities/content_type.dart';
import '../pages/chat_page.dart';
import '../pages/content_view_page.dart';
import '../pages/conversation_list_page.dart';
import '../pages/home_page.dart';
import '../pages/login_page.dart';
import '../pages/register_page.dart';
import '../pages/resource_list_page.dart';
import '../pages/splash_page.dart';
import '../pages/task_center_page.dart';
import '../pages/task_detail_page.dart';
import '../pages/upload_page.dart';
import '../providers/auth_provider.dart';
import 'app_routes.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<AuthScreenStatus>(
    ref.read(authNotifierProvider).status,
  );

  ref.listen<AuthState>(
    authNotifierProvider,
    (_, next) => refresh.value = next.status,
  );

  return GoRouter(
    initialLocation: splashRoute,
    refreshListenable: refresh,
    redirect: (context, state) {
      final status = ref.read(authNotifierProvider).status;
      final path = state.uri.path;

      if (status == AuthScreenStatus.unknown) {
        return splashRoute;
      }
      if (status == AuthScreenStatus.authenticated) {
        if (path == loginRoute || path == registerRoute) return homeRoute;
        return null;
      }
      // unauthenticated
      if (path == loginRoute || path == registerRoute) return null;
      return loginRoute;
    },
    routes: [
      GoRoute(path: splashRoute, builder: (_, __) => const SplashPage()),
      GoRoute(path: loginRoute, builder: (_, __) => const LoginPage()),
      GoRoute(path: registerRoute, builder: (_, __) => const RegisterPage()),
      GoRoute(path: homeRoute, builder: (_, __) => const HomePage()),
      GoRoute(path: uploadRoute, builder: (_, __) => const UploadPage()),
      GoRoute(
          path: resourcesRoute, builder: (_, __) => const ResourceListPage()),
      GoRoute(
          path: taskCenterRoute, builder: (_, __) => const TaskCenterPage()),
      GoRoute(
          path: conversationListRoute,
          builder: (_, __) => const ConversationListPage()),
      GoRoute(
        path: taskDetailRoute,
        builder: (_, state) =>
            TaskDetailPage(taskId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: conversationRoute,
        builder: (_, state) => ChatPage(
          conversationId: state.pathParameters['id']!,
        ),
      ),
      GoRoute(
        path: contentViewRoute,
        builder: (_, state) {
          final resourceId = state.pathParameters['id']!;
          final contentType = ContentType.fromParam(
            state.uri.queryParameters['type'],
          );
          final initialPage = int.tryParse(
            state.uri.queryParameters['page'] ?? '',
          );
          final initialTimestampMs = int.tryParse(
            state.uri.queryParameters['timestamp'] ?? '',
          );
          return ContentViewPage(
            resourceId: resourceId,
            contentType: contentType,
            initialPage: initialPage,
            initialTimestamp: initialTimestampMs == null
                ? null
                : Duration(milliseconds: initialTimestampMs),
          );
        },
      ),
    ],
  );
});
