# 技术文档：[S6-3] 实现 LlamaIndex Document/Node 元数据映射

> 版本：v1.0
> 日期：2026-07-20
> 作者：朱双泉
> 级别：AI 工程师
> 关联 PRD：[../prd/PRD_S6-3_llamaindex_node_metadata_mapping.md](../prd/PRD_S6-3_llamaindex_node_metadata_mapping.md)

---

## 1. 文档目标

定义 MKC 向量记录与 LlamaIndex Node 之间的双向映射，确保资源权限、引用跳转和分数信息在迁移中不丢失。

---

## 2. 技术栈

- Python 3.11+
- pydantic 2.x
- llama-index-core
- pytest

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 函数 | `vector_record_to_node(record)` | 内部 | 转换存储记录为 LlamaIndex Node |
| 函数 | `node_to_retrieval_chunk(node)` | 内部 | 转换检索结果为 MKC chunk |

---

## 4. 配置

无新增运行时配置。字段规范：

```yaml
metadata_required:
  - resource_id
  - user_id
  - chunk_id
metadata_optional:
  - page
  - timestamp_start
  - timestamp_end
  - source_type
```

---

## 5. 模块设计

- `metadata_mapper.py`：双向映射函数。
- `models.py`：可选定义内部 metadata TypedDict / pydantic 模型。
- 输出 `RetrievalChunk` 后继续复用 `CitationService`。

---

## 6. 关键代码实现

```python
def vector_record_to_node(record: VectorRecord) -> TextNode:
    metadata = dict(record.metadata)
    metadata.update(
        {
            "resource_id": record.resource_id,
            "user_id": record.user_id,
            "chunk_id": record.id,
        }
    )
    return TextNode(id_=record.id, text=record.text or "", metadata=metadata)


def node_with_score_to_chunk(node: NodeWithScore) -> RetrievalChunk:
    meta = dict(node.node.metadata or {})
    return RetrievalChunk(
        chunk_id=str(meta.get("chunk_id") or node.node.node_id),
        resource_id=str(meta.get("resource_id", "")),
        text=node.node.get_content() or "",
        score=float(node.score or 0.0),
        metadata=meta,
    )
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 必填 metadata 缺失 | 500 | RAG_METADATA_INVALID | 检索元数据不合法 |
| Node 内容为空 | N/A | N/A | 降级为空文本，不抛错 |

---

## 8. Web 端适配要点

确保 `page`、`timestamp_start`、`timestamp_end` 字段名与 Flutter `CitationCard` 兼容。

---

## 9. 测试策略

- 单元测试：完整 metadata、缺失可选字段、score=None、空文本。
- 安全测试：越权字段保留供后续校验，不进入 prompt-only metadata。
- 兼容测试：生成的 `RetrievalChunk` 可被 `CitationService` 使用。

---

## 10. 检查清单

- [ ] 双向映射已实现
- [ ] citation metadata 保留
- [ ] 缺字段有默认值
- [ ] 测试覆盖率 80%+
