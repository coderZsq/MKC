import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/presentation/widgets/resource_card.dart';
import 'package:mkc_client/presentation/widgets/resource_summary_text.dart';
import 'package:mkc_client/presentation/widgets/tag_chip_row.dart';

import '../../shared/resource_test_helpers.dart';

void main() {
  testWidgets('card renders summary and tags', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ResourceCard(
            resource:
                createResource(summary: '核心摘要', tags: const ['AI', '数据集']),
            onTap: () {},
            onTagTap: (_) {},
          ),
        ),
      ),
    );

    expect(find.text('核心摘要'), findsOneWidget);
    expect(find.text('AI'), findsOneWidget);
    expect(find.text('数据集'), findsOneWidget);
    expect(find.text('问答'), findsOneWidget);
  });

  testWidgets('ask button triggers callback for completed resource',
      (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ResourceCard(
            resource: createResource(status: 'completed'),
            onTap: () {},
            onAskTap: () => tapped = true,
            onTagTap: (_) {},
          ),
        ),
      ),
    );

    await tester.tap(find.text('问答'));
    expect(tapped, isTrue);
  });

  testWidgets('ask button is disabled until resource is completed',
      (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ResourceCard(
            resource: createResource(status: 'processing'),
            onTap: () {},
            onAskTap: () => tapped = true,
            onTagTap: (_) {},
          ),
        ),
      ),
    );

    await tester.tap(find.text('问答'));
    expect(tapped, isFalse);
  });

  testWidgets('card renders empty summary and tag placeholders',
      (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ResourceCard(
            resource: createResource(summary: null, tags: const []),
            onTap: () {},
            onTagTap: (_) {},
          ),
        ),
      ),
    );

    expect(find.text('暂无摘要'), findsOneWidget);
    expect(find.text('暂无标签'), findsOneWidget);
  });

  testWidgets('summary toggles expand and collapse', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ResourceSummaryText(
            summary: '很长的摘要内容，默认折叠为两行，点击展开后展示完整内容。',
            truncated: false,
          ),
        ),
      ),
    );

    expect(find.text('展开'), findsOneWidget);
    await tester.tap(find.text('展开'));
    await tester.pump();
    expect(find.text('收起'), findsOneWidget);
    await tester.tap(find.text('收起'));
    await tester.pump();
    expect(find.text('展开'), findsOneWidget);
  });

  testWidgets('tag row is horizontally scrollable and clickable',
      (tester) async {
    String? tapped;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 180,
            child: TagChipRow(
              tags: List.generate(12, (index) => '标签$index'),
              onTagTap: (tag) => tapped = tag,
            ),
          ),
        ),
      ),
    );

    expect(find.byType(ListView), findsOneWidget);
    await tester.tap(find.text('标签0'));
    expect(tapped, '标签0');
  });
}
