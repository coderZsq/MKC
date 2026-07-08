# S2-1 测试用例：集成 faster-whisper 实现 ASR

## 1. 范围与目标

验证 AI Service 中 faster-whisper ASR 转录链路：模型加载、音频预处理、分片转录、接口响应、进度上报、错误处理与测试覆盖率。

## 2. 测试环境

- Python 3.11+
- faster-whisper 1.0+
- ffmpeg 已安装
- Redis + Celery Worker 已启动
- Gateway 健康且可接收内部进度上报
- 测试音频：MP3/WAV/M4A 样本文件

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-1-001 | Functional | Integration | P0 | 提交 ASR 任务成功 | 音频文件已上传 | POST /ai/v1/asr | 返回 task_id，状态 pending | PRD AC-1 |
| MKC-TC-S2-1-002 | Functional | Integration | P0 | ASR 任务完成并返回转录文本 | Worker 已启动 | 等待任务完成 | 状态 completed，segments 非空 | PRD AC-5 |
| MKC-TC-S2-1-003 | Functional | Unit | P1 | 音频转码为 16kHz WAV | 提供 MP3 | 调用 AudioProcessor.convert_to_wav | 输出 WAV 16kHz 单声道 | PRD AC-3 |
| MKC-TC-S2-1-004 | Functional | Unit | P1 | 长音频正确分片 | 提供 60s WAV | 调用 chunk_audio(chunk_length=30) | 返回 2 段以上 | PRD AC-4 |
| MKC-TC-S2-1-005 | Functional | Unit | P1 | 输出包含时间戳与置信度 | mock segments | 调用 WhisperEngine.transcribe | 每条含 start/end/text/confidence | PRD AC-5 |
| MKC-TC-S2-1-006 | Functional | Integration | P1 | 进度上报到 Gateway | 运行任务 | 查看任务进度 | progress 单调递增 | PRD AC-6 |
| MKC-TC-S2-1-007 | Functional | Unit | P2 | 支持多模型配置切换 | 配置 model=base | 加载模型 | 加载 base 模型成功 | PRD AC-2 |
| MKC-TC-S2-1-008 | Functional | Integration | P2 | 支持 M4A/WAV 输入 | 提供 M4A/WAV | 提交任务 | 任务成功完成 | PRD AC-3 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-1-009 | Security | Integration | P0 | 缺少内部 Key 拒绝访问 | 请求头无 Key | POST /ai/v1/asr | 返回 401 | TECH 3 |
| MKC-TC-S2-1-010 | Security | Integration | P1 | 错误 Key 拒绝访问 | 使用错误 Key | POST /ai/v1/asr | 返回 403 | TECH 3 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-1-011 | Negative | Integration | P0 | 损坏音频返回 400 | 提供损坏 MP3 | 提交任务 | 返回 INVALID_AUDIO | PRD AC-7 |
| MKC-TC-S2-1-012 | Negative | Integration | P1 | 模型路径不存在返回 503 | 配置错误 model_dir | 启动服务 | 返回 MODEL_LOAD_ERROR | TECH 7 |
| MKC-TC-S2-1-013 | Negative | Integration | P1 | 任务失败触发状态更新 | 模拟转录异常 | 等待任务 | 任务状态 failed | PRD AC-7 |
| MKC-TC-S2-1-014 | Negative | Unit | P1 | 转码失败抛出 AudioProcessingError | 提供非音频文件 | 调用 convert_to_wav | 抛出异常 | PRD AC-3 |
| MKC-TC-S2-1-015 | Reliability | Integration | P1 | 模型加载失败自动 fallback | 配置 large-v3 但显存不足 | 启动任务 | 使用 fallback 模型 | PRD 降级策略 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-1-016 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-8 |
| MKC-TC-S2-1-017 | Functional | Static | P1 | mypy / ruff 通过 | 代码存在 | 运行 ruff check + mypy | 0 issues | 工程规范 |
| MKC-TC-S2-1-018 | Security | Static | P1 | 无硬编码 API Key | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |
| MKC-TC-S2-1-019 | Functional | Unit | P1 | 无显存泄漏 | 多次转录 | 监控内存 | 内存稳定 | 阻塞风险 |

### 3.5 性能与兼容性

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-1-020 | Performance | Integration | P2 | 1 分钟音频 30s 内完成 | 1 分钟音频 | 提交任务 | 完成时间 < 30s（small 模型） | PRD 性能 |
| MKC-TC-S2-1-021 | Compatibility | Unit | P2 | CPU 与 CUDA 设备均可加载 | 配置 device | 加载模型 | 无异常 | PRD AC-2 |

## 4. 测试执行清单

- [ ] ASR 任务提交与完成
- [ ] 音频转码与分片
- [ ] 转录结果含时间戳与置信度
- [ ] 进度上报到 Gateway
- [ ] 错误/异常处理与错误码
- [ ] 模型 fallback
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
