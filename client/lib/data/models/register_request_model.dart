/// Registration request payload.
class RegisterRequestModel {
  const RegisterRequestModel({
    required this.email,
    required this.password,
    this.nickname,
  });

  final String email;
  final String password;
  final String? nickname;

  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'email': email,
      'password': password,
    };
    if (nickname != null) {
      json['nickname'] = nickname;
    }
    return json;
  }
}
