import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/app.dart';

void main() {
  testWidgets('MKCApp renders title text', (WidgetTester tester) async {
    await tester.pumpWidget(const MKCApp());

    expect(find.text('MKC — Multimedia Knowledge Companion'), findsOneWidget);
  });
}
