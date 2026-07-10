# MKC 项目 S0-1 踩坑实录：GitHub 仓库治理与目录结构初始化

> 项目：MKC（Multimedia Knowledge Companion）
> 阶段：S0-1 GitHub 仓库治理与目录结构设计
> 时间：2026-07-07
> 目标读者：准备用 Flutter + Go + Python 搭建全栈项目、并想一步到位的开发者

---

## 一、S0-1 到底做了什么

S0-1 是整个 MKC 项目的地基阶段，目标不是写业务代码，而是把**仓库治理、目录结构、CI、文档模板**全部搭好，让后续 Sprint 能专注于功能开发。

最终交付物包括：

| 模块 | 内容 |
|------|------|
| 仓库治理 | Public 仓库、MIT License、main 分支保护、GitHub Project 看板 |
| 目录结构 | `client/` Flutter、`gateway/` Go、`ai-service/` Python、`infra/` K8s、`docs/` 文档 |
| CI/CD | 3 条 GitHub Actions：Flutter 分析/测试、Go lint/测试、Python black/pytest |
| 文档模板 | PR 模板、Bug/Feature Issue 模板、README 骨架 |
| 初始代码 | 各服务的占位入口、第一个 Widget 测试、第一个 Flask health 接口测试 |

检查清单 5/5 全部完成，PR #1 已成功合并到 main。

---

## 二、踩坑清单与解决方案

### 坑 1：git push 走 SSH 被断开

**现象：**
```
Connection closed by ... port 22
fatal: Could not read from remote repository
```

**原因：** 本地 remote 配的是 SSH，但当前网络环境对 22 端口不友好。

**解决：** 把 remote 切到 HTTPS。
```bash
git remote set-url origin https://github.com/coderZsq/MKC.git
```

**经验：** 个人开发机如果 SSH 不稳定，先切 HTTPS 验证网络；后面再切回 SSH 配 deploy key 也不迟。

---

### 坑 2：Flutter CI 报 `sort_pub_dependencies`

**现象：**
```
info • Sort pub dependencies • client/pubspec.yaml:23:1 • sort_pub_dependencies
```

**原因：** `pubspec.yaml` 里的依赖不是严格按字母序排列。`analysis_options.yaml` 启用了 `sort_pub_dependencies` lint。

**解决：** 把所有 `dependencies`、`dev_dependencies` 按字母顺序重排。

```yaml
dependencies:
  cupertino_icons: ^1.0.8
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.5.1
  freezed_annotation: ^2.4.1
  go_router: ^14.1.4
  intl: ^0.19.0          # 注意这里
  json_annotation: ^4.9.0
```

**经验：** 不要依赖人工检查，提交前本地跑 `flutter analyze`，CI 会和你用同一个规则。

---

### 坑 3：Python CI 被 `black` 格式化拦截

**现象：**
```
would reformat ai-service/celery_workers/celery_app.py
Oh no! 💥 💔 💥
```

**原因：** Celery 的 task 函数前缺少一个空行，`black` 要求在模块级函数/类之间保持统一格式。

**解决：** 在 `@celery_app.task` 装饰器前加一个空行。

```python
from celery import Celery

# Sprint 0 占位：真实配置在 config 加载后注入
celery_app = Celery("ai-service")


@celery_app.task
def add(x: int, y: int) -> int:
    return x + y
```

**经验：** Python 项目提交前跑 `black --check .`，比 CI 报错后再修快得多。

---

### 坑 4：CI 提示没有测试文件

**现象 1（Flutter）：**
```
Test directory does not appear to contain any test files.
```

**现象 2（Python）：**
```
no tests ran
```

**原因：** CI 配置里要求跑测试，但仓库里确实没有测试文件。

**解决：** 各补一个最小占位测试，确保 CI 有东西可跑。

Flutter：
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mkc_client/app.dart';

void main() {
  testWidgets('MKCApp renders title text', (WidgetTester tester) async {
    await tester.pumpWidget(const MKCApp());
    expect(find.text('MKC — Multimedia Knowledge Companion'), findsOneWidget);
  });
}
```

Python：
```python
import pytest
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "ai-service"}
```

**经验：** 项目初始化时就写好第一个测试，哪怕只是占位。这能验证：
- 测试框架能正确发现用例
- 包导入路径没问题
- CI 的测试命令能正常退出

---

### 坑 5：Flutter `intl` 版本冲突

**现象：**
```
Because mkc_client depends on intl ^0.20.2 which doesn't match any versions, version solving failed.
```

**原因：** CI 里用的是 Flutter 3.22.x，该版本 SDK 自带的 `intl` 兼容上限是 `0.19.0`。本地开发环境可能是 Flutter 3.24+，所以写成了 `^0.20.2`。

**解决：** 把 `pubspec.yaml` 里的 `intl` 降到 `^0.19.0`，与 CI 环境保持一致。

```yaml
dependencies:
  intl: ^0.19.0
```

**经验：** 多服务项目的依赖版本要以 CI 环境为准，不能只看本地。可以在 CI workflow 里打印 `flutter --version` 和 `go version`、`python --version`，方便排查。

---

### 坑 6：Python 测试找不到 `app` 模块

**现象：**
```
ModuleNotFoundError: No module named 'app'
```

**原因：**
1. `ai-service/app/` 目录下没有 `__init__.py`，Python 不把它当包；
2. 测试运行时，项目根目录不在 `PYTHONPATH` 里。

**解决：**
1. 添加 `ai-service/app/__init__.py`；
2. 添加 `ai-service/tests/conftest.py`，把项目根目录注入 `sys.path`：

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

**经验：** 小型项目用 `conftest.py` + `sys.path` 最简单；项目变大后应改用 `pytest.ini` 配 `pythonpath`，或者把包安装成 editable：`pip install -e .`。

---

### 坑 7：Flutter 测试里有未使用的 import

**现象：**
```
unused_import • client/test/app_test.dart:1:8
```

**原因：** 测试文件里写了 `import 'package:flutter/material.dart';` 但实际上没用到。

**解决：** 删除未使用的 import。

**经验：** `analysis_options.yaml` 里启用 `unused_import` 是基本操作，养成随手清理 import 的习惯。

---

### 坑 8：GitHub Project 看板创建需要 `project` scope

**现象：**
```
gh project create ...
# 报错：缺少 project scope
```

**原因：** 默认 `gh auth login` 拿到的 token 不一定包含 `project` scope。

**解决：**
```bash
gh auth refresh -h github.com -s read:project,project
```

如果网络导致 device auth 失败，也可以直接去 GitHub UI 创建 Project，然后更新检查清单。

**经验：** 用 `gh auth status` 随时检查 token scopes；涉及 Project、Org、Pages 等高级操作时，先确认 scope 够不够。

---

### 坑 9：PR 合并被分支保护拦住

**现象：**
```
mergeStateStatus: BLOCKED
reviewDecision: REVIEW_REQUIRED
```

**原因：** main 分支保护规则要求至少 1 个 approving review，但单人项目没有第二个人可以 approve。

**解决：** 两个方案：

**方案 A（推荐）：** 在 GitHub UI 打开 PR，勾选 **Merge without waiting for requirements to be met (administrators only)** 直接合并。

**方案 B：** 临时去 `Settings → Branches → main → Edit`，取消 **Require a pull request before merging**，合并后再恢复。

**经验：** 单人项目配置分支保护时，可以开启 **Allow specified actors to bypass required pull requests** 并把 owner 加进去；或者干脆把 required approving review count 设为 0，只保留 "禁止 force push" 和 "要求 up-to-date"。

---

## 三、S0-1 的目录结构速览

```
mkc/
├── .github/               # CI/CD、Issue/PR 模板
├── client/                # Flutter
├── gateway/               # Go
├── ai-service/            # Python + Celery
├── infra/                 # K8s、部署脚本
├── docs/                  # PRD、技术文档、运维手册
├── .editorconfig
├── .gitignore
├── LICENSE
└── README.md
```

这个结构的好处是**按服务一级划分**，每个服务独立演进、独立 CI，避免跨服务引用。

---

## 四、给后来者的建议

1. **先搭 CI，再写业务。** 第一个 PR 就把 Flutter / Go / Python 的 CI 跑通，后面每次提交都有反馈。
2. **测试从第一个占位开始。** 不要等"业务成熟了再补测试"，先让 CI 有测试可跑。
3. **依赖版本以 CI 为准。** 本地环境可以新，但 CI 必须能复现。
4. **分支保护要可落地。** 单人项目不要把规则设成自己 merge 不了的程度，保留 admin bypass 或自 review 通道。
5. **文档和代码一起提交。** PR 模板、Issue 模板、README 骨架都要在第一个 Sprint 就位。

---

## 五、下一步

S0-1 已经合进 main，接下来进入 S0-2：本地 K8s 清单与部署脚本。目标是让 `infra/scripts/local-up.sh` 能一键拉起开发环境。

---

*本文由 Claude Code 协助整理，基于 MKC 项目 S0-1 真实踩坑记录。*
