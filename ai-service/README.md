# MKC AI Service

Python AI 服务，基于 Flask + Celery。

## 目录结构

```
ai-service/
├── app/                # Flask 应用
│   ├── api/
│   ├── core/
│   └── services/
├── celery_workers/     # Celery Worker
├── config/             # 配置
├── models/             # 模型权重（gitignored）
└── tests/
```

## 启动

```bash
cd ai-service
python -m venv .venv
source .venv/bin/activate
make install
cp config/.env.example .env
make run
```

## 测试

```bash
make test
```

## Docker

```bash
make build
```
