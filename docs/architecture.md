# MKC 系统架构

详见 [TECH_STACK.md](./TECH_STACK.md) 与 [TECH_S0-2_local_k8s_manifests.md](./TECH_S0-2_local_k8s_manifests.md)。

## 架构图

<!-- 后续补充 Mermaid 或图片 -->

## 核心组件

- 客户端：Flutter
- 网关：Go + Gin
- AI 服务：Python + Flask + Celery
- 数据层：MySQL + Redis + MinIO + Milvus
- 基础设施：Docker Desktop Kubernetes / 云 K8s
