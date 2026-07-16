# 技术文档：[S5-9] 编写技术博客/掘金文章

> 版本：v1.0
> 日期：2026-07-16
> 作者：朱双泉
> 级别：后端/前端/AI 工程师
> 关联 PRD：[../prd/PRD_S5-9_technical_blog_article.md](../prd/PRD_S5-9_technical_blog_article.md)

---

## 1. 文档目标

定义技术博客的内容结构、素材来源、发布格式、脱敏要求和检查方式。

---

## 2. 技术栈

- Markdown
- Mermaid / PNG 素材
- markdownlint-cli
- 链接检查工具

---

## 3. 接口契约

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| 文档 | `docs/blog/mkc_project_review.md` | 无 | 博客正文 |
| 资产 | `docs/blog/assets/*` | 无 | 架构图与截图 |

不涉及运行时 API。

---

## 4. 配置

```yaml
blog:
  target_platform: juejin
  max_images: 6
  require_redaction: true
```

---

## 5. 模块设计

- 开篇：项目背景与目标。
- 架构：端到端组件和数据流。
- 核心实现：上传、解析、RAG、Agent、引用。
- 生产化：评估、可观测性、K8s。
- 复盘：难点、取舍、不足、下一步。

---

## 6. 关键代码实现

```markdown
## 从文件到可引用回答的链路

1. 上传 MP3/PDF
2. 异步解析与切块
3. Embedding 写入 Milvus
4. 检索、重排、LLM 生成
5. 引用溯源与跳转
```

---

## 7. 错误映射

| 场景 | HTTP 状态 | Error Code | Message |
|---|---|---|---|
| 素材缺失 | N/A | BLOG_ASSET_MISSING | 博客素材缺失 |
| 链接失效 | N/A | BLOG_LINK_BROKEN | 博客链接失效 |
| 敏感信息泄露 | N/A | BLOG_SECRET_DETECTED | 博客包含敏感信息 |

---

## 8. Web 端适配要点

图片使用相对路径，确保发布平台和移动端阅读时不横向溢出。

---

## 9. 测试策略

- 静态测试：Markdown lint、链接检查。
- 人工 review：技术准确性、脱敏、截图质量。
- 发布预览：掘金或个人博客编辑器预览。

---

## 10. 检查清单

- [ ] 博客正文完成
- [ ] 素材已脱敏
- [ ] Markdown lint 与链接检查通过
