import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/core/platform/platform_capabilities.dart';
import 'package:mkc_client/presentation/pages/chat_page.dart';
import 'package:mkc_client/presentation/pages/upload_page.dart';
import 'package:mkc_client/presentation/providers/chat_provider.dart';
import 'package:mkc_client/presentation/providers/upload_provider.dart';
import 'package:mkc_client/shared/errors/app_exception.dart';
import 'package:mkc_client/shared/result.dart';

import '../shared/chat_test_helpers.dart';
import '../shared/upload_test_helpers.dart';

void main() {
  group('multiplatform widget smoke', () {
    for (final width in <double>[390, 834, 1440]) {
      testWidgets('upload page fits width $width', (tester) async {
        tester.view.physicalSize = Size(width, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              platformCapabilitiesProvider.overrideWithValue(
                const PlatformCapabilities(
                  supportsFilePicker: true,
                  supportsSse: true,
                  isWeb: false,
                  isMobile: true,
                  isDesktop: false,
                  uploadsRequireInMemoryBytes: false,
                  maxUploadBytes: PlatformUploadLimits.native,
                ),
              ),
            ],
            child: const MaterialApp(home: UploadPage()),
          ),
        );
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.text('选择文件'), findsOneWidget);
      });

      testWidgets('chat page fits width $width', (tester) async {
        tester.view.physicalSize = Size(width, 900);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        final repository = FakeChatRepository()
          ..nextMessagesResult = const Result.success([]);

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              chatRepositoryProvider.overrideWithValue(repository),
            ],
            child: const MaterialApp(
              home: ChatPage(conversationId: 'conv-1'),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(TextField), findsOneWidget);
      });
    }

    testWidgets('stream disconnect shows retry action', (tester) async {
      final repository = FakeChatRepository()
        ..nextMessagesResult = const Result.success([])
        ..streamError = const StreamDisconnectedException();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            chatRepositoryProvider.overrideWithValue(repository),
          ],
          child: const MaterialApp(
            home: ChatPage(conversationId: 'conv-1'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'Question');
      await tester.tap(find.byIcon(Icons.send));
      await tester.pumpAndSettle();

      expect(find.text('回答连接已断开，请重试'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });

    testWidgets('upload picker failure shows friendly error', (tester) async {
      final picker = FakeFilePickerService()
        ..nextError = const FilePickerFailedException();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            filePickerServiceProvider.overrideWithValue(picker),
          ],
          child: const MaterialApp(home: UploadPage()),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('选择文件'));
      await tester.pumpAndSettle();

      expect(find.text('文件选择失败，请重试'), findsOneWidget);
    });
  });
}
