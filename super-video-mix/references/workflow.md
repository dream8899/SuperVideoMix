# 工作流与状态

## 目录

1. 阶段
2. Job state
3. Job workspace
4. Review gate
5. 退出码

## 1. 阶段

固定使用以下顺序：

```text
discover → probe → dedupe → analyze → multi-theme split preflight → crop preflight → screening/schedule → plan → review gate
  → clean → transform → encode → verify → deliver
```

`analyze` 和 `plan` 不渲染视频。`apply` 只能执行已保存且通过校验的计划。执行阶段不得临时改变参数；先写同目录临时文件，完整解码和规格验证通过后再无覆盖交付。

顶部对齐 3:4 裁切必须先运行 `crop_3x4_preflight.py`。预判只提供内容风险排序，不替代人工观看红线预览；只有用户批准的 `适合` 或指定 `人工复核` 项才能进入 plan。

多主题长视频必须先分析。**首选内容感知法**（`content_split.py`），从 scene scores 做峰值检测不预设节拍；若段长均匀再考虑节拍法（`split_multitheme_video.py`）比较 10/15 秒拼接节奏。

分析阶段关键参数：min_height=0.15、min_distance=1.5s（聚合同一转场的多个峰）、min_segment=2.0s、过滤距开头<3s 的切点。置信度 high≥0.4 / medium≥0.25 / low<0.25。

必须查看预览帧、核对边界、段数和内容命名后，才能执行。拆分输出必须逐段完整解码验证并生成 `拆分清单.tsv`。

## 2. Job state

使用稳定英文枚举：

- `discovered`
- `analyzed`
- `planned`
- `running`
- `verified`
- `failed`
- `skipped_duplicate`

只允许状态向前迁移；重试失败项时保留上一次错误上下文。

## 3. Job workspace

```text
JOB_DIR/
├── input.json
├── analysis.json
├── plan.json
├── execution.json
├── verification.json
├── logs/
├── previews/
└── output/
```

源文件保持只读。执行时先写 job 内的临时文件，验证成功后再移交到最终输出位置。

## 4. Review gate

进入 `apply` 前逐项确认：

1. 输入哈希匹配。
2. 输出路径不是输入路径且不会隐式覆盖。
3. 操作顺序与用户意图一致。
4. `auto` 参数已经展开并固定。
5. 所有 high-risk operation 已预览并批准。
6. 预期时长、尺寸、帧率和音轨明确。
7. `needs_review` conflict 已显式批准。
8. 3:4 顶部裁切项已在筛选清单中获批，且预览红线未穿过关键主体。
9. 多主题拆分项已观看联系表，切点没有落在动作中段，片尾黑屏已排除，逐段名称与内容一致。

## 5. 退出码

| Code | Name | 含义 |
|---:|---|---|
| 0 | `OK` | 成功 |
| 2 | `USAGE_ERROR` | CLI 参数错误 |
| 3 | `INPUT_ERROR` | 输入、路径或媒体无效 |
| 4 | `TOOL_ERROR` | FFmpeg/ffprobe 缺失或失败 |
| 5 | `PLAN_ERROR` | schema、plan hash、审批或输入哈希失败 |
| 6 | `NOT_IMPLEMENTED` | 当前阶段未实现 |
| 7 | `VERIFY_ERROR` | 输出验证失败 |
