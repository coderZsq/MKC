# MKC - Multimedia AI Knowledge Companion

![CI - Gateway](https://github.com/coderZsq/mkc/actions/workflows/ci-gateway.yml/badge.svg)
![CI - AI Service](https://github.com/coderZsq/mkc/actions/workflows/ci-ai-service.yml/badge.svg)
![CI - Client](https://github.com/coderZsq/mkc/actions/workflows/ci-client.yml/badge.svg)

基于 Flutter + Go + Python 的多媒体 AI 知识库助手。

## 核心能力

- MP3 转录为 SRT 与文本
- PDF 解析为结构化文本
- 基于 RAG 的知识库问答
- 多轮 SSE 流式对话

## 技术栈

- 前端：Flutter + Clean Architecture + Riverpod
- 网关：Go + Gin + GORM + MySQL + Redis
- AI 服务：Python + Flask + Celery + LangGraph + LlamaIndex
- 基础设施：Kubernetes + nginx-ingress + MinIO + Milvus

## 快速开始

见 [docs/](./docs/) 目录。

## 目录结构

见 [技术文档 TECH_S0-1](./docs/tech/TECH_S0-1_github_repo_init.md)。

## API 文档

API 接口契约位于 [docs/api/openapi.yaml](docs/api/openapi.yaml)，设计说明见 [docs/api/api-design.md](docs/api/api-design.md)。

Gateway 启动后，可通过 Swagger UI 在线查看文档：

```text
http://mkc.local/swagger/index.html
```

本地开发环境请替换 `mkc.local` 为实际服务地址。

## License

MIT
