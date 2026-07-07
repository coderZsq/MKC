import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/env.dart';
import '../../data/datasources/remote/api_client.dart';
import '../../data/datasources/secure/secure_token_storage.dart';
import '../../domain/repositories/token_provider.dart';

final tokenProvider = Provider<TokenProvider>((ref) {
  return SecureTokenStorage();
});

final apiClientProvider = Provider<ApiClient>((ref) {
  final token = ref.watch(tokenProvider);
  return ApiClient(baseUrl: Env.baseUrl, tokenProvider: token);
});
