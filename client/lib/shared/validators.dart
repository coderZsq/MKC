/// Form validation helpers used by login and registration pages.
String? validateEmail(String? value) {
  if (value == null || value.isEmpty) {
    return '请输入邮箱';
  }
  if (!_emailRegex.hasMatch(value)) {
    return '邮箱格式不正确';
  }
  return null;
}

String? validatePassword(String? value) {
  if (value == null || value.length < 8) {
    return '密码至少 8 位';
  }
  if (!_passwordRegex.hasMatch(value)) {
    return '密码需同时包含字母和数字';
  }
  return null;
}

String? validateConfirmPassword(String? password, String? confirm) {
  if (password != confirm) {
    return '两次输入的密码不一致';
  }
  return null;
}

final _emailRegex = RegExp(
  r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",
);

final _passwordRegex = RegExp(r'(?=.*[A-Za-z])(?=.*\d)');
