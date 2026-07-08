import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/shared/validators.dart';

void main() {
  group('validateEmail', () {
    test('returns required message for null', () {
      expect(validateEmail(null), equals('请输入邮箱'));
    });

    test('returns required message for empty string', () {
      expect(validateEmail(''), equals('请输入邮箱'));
    });

    test('returns format error for invalid email', () {
      expect(validateEmail('not-email'), equals('邮箱格式不正确'));
      expect(validateEmail('user@'), equals('邮箱格式不正确'));
      expect(validateEmail('@example.com'), equals('邮箱格式不正确'));
    });

    test('returns null for valid email', () {
      expect(validateEmail('user@example.com'), isNull);
      expect(validateEmail('user+tag@example.co.uk'), isNull);
    });
  });

  group('validatePassword', () {
    test('returns required message for null or empty', () {
      expect(validatePassword(null), equals('密码至少 8 位'));
      expect(validatePassword(''), equals('密码至少 8 位'));
    });

    test('returns length error for short password', () {
      expect(validatePassword('short1'), equals('密码至少 8 位'));
      expect(validatePassword('a1'), equals('密码至少 8 位'));
    });

    test('returns format error when password lacks digit', () {
      expect(validatePassword('password'), equals('密码需同时包含字母和数字'));
      expect(validatePassword('PasswordOnly'), equals('密码需同时包含字母和数字'));
    });

    test('returns format error when password lacks letter', () {
      expect(validatePassword('12345678'), equals('密码需同时包含字母和数字'));
    });

    test('returns null for valid password', () {
      expect(validatePassword('Password1'), isNull);
      expect(validatePassword('p@ssw0rd123'), isNull);
    });
  });

  group('validateConfirmPassword', () {
    test('returns mismatch error when passwords differ', () {
      expect(
        validateConfirmPassword('Password1', 'Password2'),
        equals('两次输入的密码不一致'),
      );
    });

    test('returns null when passwords match', () {
      expect(validateConfirmPassword('Password1', 'Password1'), isNull);
    });
  });
}
