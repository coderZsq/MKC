# S2-2 测试用例：生成 SRT 字幕文件

## 1. 范围与目标

验证 SRT 字幕生成逻辑：时间码格式化、片段合并、SRT 输出、MinIO 上传与错误处理。

## 2. 测试环境

- Python 3.11+
- MinIO 服务可用
- 测试 segments 数据
- MinIO mock 或本地服务

## 3. 测试用例

### 3.1 功能/正例

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-2-001 | Functional | Unit | P0 | 标准 SRT 生成 | 提供 3 条 segments | 调用 generate_srt | 输出符合 SRT 规范 | PRD AC-1 |
| MKC-TC-S2-2-002 | Functional | Unit | P0 | 时间码格式正确 | 提供时间 5.0s / 8.2s | 调用 format_timecode | 输出 00:00:05,000 --> 00:00:08,200 | PRD AC-2 |
| MKC-TC-S2-2-003 | Functional | Unit | P0 | 相邻短句合并 | 提供 0.5s 短句 | 调用 merge_segments | 合并后时长 >= 1s | PRD AC-3 |
| MKC-TC-S2-2-004 | Functional | Unit | P1 | 超长文本拆分 | 提供 100 字单句 | 调用合并/拆分 | 结果不超过 80 字 | PRD AC-3 |
| MKC-TC-S2-2-005 | Functional | Integration | P1 | SRT 文件上传 MinIO | 生成 SRT 内容 | 调用 save_to_minio | 返回可访问 URL | PRD AC-4 |
| MKC-TC-S2-2-006 | Functional | Unit | P2 | 支持 WebVTT 导出 | 配置 output_format=vtt | 调用 generate | 输出 VTT 格式 | PRD AC-5 |

### 3.2 权限/安全

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-2-007 | Security | Integration | P1 | MinIO 签名 URL 不过期过短 | 上传完成 | 检查 URL 过期时间 | 过期时间 >= 1 小时 | 安全基线 |

### 3.3 错误/异常

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-2-008 | Negative | Unit | P0 | 空 segments 抛出异常 | 提供空列表 | 调用 generate_srt | 抛出 EMPTY_SEGMENTS | PRD AC-6 |
| MKC-TC-S2-2-009 | Negative | Integration | P1 | MinIO 上传失败返回错误 | 模拟 MinIO 异常 | 调用 save_to_minio | 返回 STORAGE_ERROR | PRD AC-6 |
| MKC-TC-S2-2-010 | Negative | Unit | P1 | 非法时间戳处理 | 提供 end < start | 调用 merge_segments | 修复或抛出异常 | PRD 阻塞风险 |

### 3.4 代码质量

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-2-011 | Functional | Static | P1 | pytest 覆盖率 80%+ | 代码存在 | 运行 pytest --cov | coverage >= 80% | PRD AC-7 |
| MKC-TC-S2-2-012 | Functional | Static | P1 | ruff / mypy 通过 | 代码存在 | 运行静态检查 | 0 issues | 工程规范 |
| MKC-TC-S2-2-013 | Security | Static | P1 | 无硬编码 MinIO 凭证 | 代码存在 | 全局搜索 | 仅 .env 出现 | 安全基线 |

### 3.5 Web 兼容

| ID | 维度 | 级别 | 优先级 | 用例标题 | 前提条件 | 执行步骤 | 预期结果 | 关联需求 |
|---|---|---|---|---|---|---|---|---|
| MKC-TC-S2-2-014 | Compatibility | Unit | P2 | SRT 可在 Web 解析 | 生成 SRT | 按行解析 | 字幕列表正确 | PRD Web 适配 |

## 4. 测试执行清单

- [ ] SRT 格式输出正确
- [ ] 时间码格式正确
- [ ] 短句合并
- [ ] MinIO 上传成功
- [ ] 空 segments / 上传失败错误处理
- [ ] 覆盖率 80%+
- [ ] 静态检查通过
- [ ] 无硬编码密钥

## 5. 缺陷记录模板

| 用例 ID | 缺陷描述 | 严重程度 | 复现步骤 | 预期 | 实际 | 状态 |
|---|---|---|---|---|---|---|
| | | | | | | |
