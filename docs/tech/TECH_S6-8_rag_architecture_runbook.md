# 技术文档：[S6-8] 更新 RAG 架构文档与调试 Runbook

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：后端/前端/AI 工程师
> 关联 PRD：[../prd/PRD_S6-8_rag_architecture_runbook.md](../prd/PRD_S6-8_rag_architecture_runbook.md)

---

## 1. 文档目标

定义 Sprint 6 收尾文档更新范围：架构图、RAG 双引擎说明、Runbook、验证命令、故障排查和回滚步骤。

---

## 2. 技术栈

- Markdown / Mermaid
- markdownlint-cli
- markdown-link-check

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 文档 | `docs/ARCHITECTURE.md` | 无 | 更新 RAG 双引擎架构 |
| 文档 | `docs/runbooks/llamaindex_rag.md` | 无 | 新增调试和回滚 Runbook |

---

## 4. 配置

Runbook 必须说明：

```bash
RAG_ENGINE=legacy
RAG_ENGINE=llamaindex
```

---

## 5. 模块设计

- `ARCHITECTURE.md`：更新 Chat and RAG Flow。
- `llamaindex_rag.md`：包含配置、验证、评估、排障、回滚。
- README 可选增加 Runbook 链接。

---

## 6. 关键代码实现

```markdown
## Rollback

1. Set `RAG_ENGINE=legacy`.
2. Restart AI Service and Celery worker if they load RAG config.
3. Run smoke QA and eval comparison.
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 文档链接失效 | N/A | DOC_LINK_BROKEN | 文档链接失效 |
| 命令不可执行 | N/A | DOC_COMMAND_INVALID | 文档命令不可执行 |

---

## 8. Web 端适配要点

Runbook 包含 Flutter Web Chat smoke 测试步骤：启动 Web、提问、检查 chunk/citation/done。

---

## 9. 测试策略

- markdownlint。
- markdown-link-check。
- 人工检查命令路径和配置名称。

---

## 10. 检查清单

- [ ] 架构文档已更新
- [ ] Runbook 已新增
- [ ] 回滚步骤清晰
- [ ] markdownlint 通过
- [ ] link check 通过
