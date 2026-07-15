import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/errors/error_mapper.dart';
import '../../shared/validators.dart';
import '../providers/auth_provider.dart';
import '../routes/app_routes.dart';
import '../widgets/claude_layout.dart';

/// Registration screen with email/password/confirm-password/nickname form.
class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _nicknameController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;

    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final nickname = _nicknameController.text.trim().isEmpty
        ? null
        : _nicknameController.text.trim();

    ref.read(authNotifierProvider.notifier).register(
          email,
          password,
          nickname: nickname,
        );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authNotifierProvider);

    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 440),
                      child: ClaudePanel(
                        padding: const EdgeInsets.all(22),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _buildHeader(),
                            const SizedBox(height: 20),
                            _buildForm(state),
                            const SizedBox(height: 12),
                            if (state.error != null)
                              Text(
                                mapAuthErrorToMessage(state.error),
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            const SizedBox(height: 12),
                            _buildSubmitButton(state),
                            const SizedBox(height: 12),
                            _buildLoginLink(),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primary,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            Icons.person_add_outlined,
            color: Theme.of(context).colorScheme.onPrimary,
          ),
        ),
        const SizedBox(height: 12),
        const ClaudeEyebrow('Create account'),
        const SizedBox(height: 6),
        Text(
          '注册 MKC',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
      ],
    );
  }

  Widget _buildForm(AuthState state) {
    return Form(
      key: _formKey,
      child: AutofillGroup(
        child: Column(
          children: [
            TextFormField(
              controller: _emailController,
              enabled: !state.isLoading,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.email],
              decoration: const InputDecoration(
                labelText: '邮箱',
                hintText: '请输入邮箱',
                prefixIcon: Icon(Icons.email_outlined),
              ),
              validator: validateEmail,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _nicknameController,
              enabled: !state.isLoading,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: '昵称（可选）',
                hintText: '请输入昵称',
                prefixIcon: Icon(Icons.person_outline),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _passwordController,
              enabled: !state.isLoading,
              obscureText: true,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.newPassword],
              decoration: const InputDecoration(
                labelText: '密码',
                hintText: '请输入密码',
                prefixIcon: Icon(Icons.lock_outlined),
              ),
              validator: validatePassword,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _confirmPasswordController,
              enabled: !state.isLoading,
              obscureText: true,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.newPassword],
              onFieldSubmitted: (_) => _submit(),
              decoration: const InputDecoration(
                labelText: '确认密码',
                hintText: '请再次输入密码',
                prefixIcon: Icon(Icons.lock_outlined),
              ),
              validator: (value) => validateConfirmPassword(
                _passwordController.text,
                value,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSubmitButton(AuthState state) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: state.isLoading ? null : _submit,
        child: state.isLoading
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Text('注册'),
      ),
    );
  }

  Widget _buildLoginLink() {
    return TextButton(
      onPressed: () => context.go(loginRoute),
      child: const Text('已有账号？去登录'),
    );
  }
}
