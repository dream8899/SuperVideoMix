---
name: super-video-mix
description: 面向抖音、TikTok、Instagram Reels、YouTube Shorts 等授权短视频，执行素材去重、多主题长视频精准拆分、废片尾分析与清理、固定水印或硬字幕区域处理、3:4 裁切、轻度放大、高清增强、重新构图、镜像反转、调色、降噪、锐化、音画同步变速、发布文案核验和输出验证。Use when Codex needs to analyze, split, deduplicate, crop, enhance, transform, name, prepare copy, or verify authorized short-form videos with reviewable plans and without overwriting source files.
---

# SuperVideoMix 短视频清理、翻新与发布准备

## 核心原则

先分析，再生成稳定 JSON 计划，审查后才执行。将“清理”和“翻新”建模为独立操作，不用镜像、裁边、调色或噪声扰动宣称规避平台检测。

始终遵守：

1. 只处理用户自有或已获授权的内容；涉及水印、硬字幕或归属信息时先确认授权和区域。
2. 默认只读源文件，输出不得与输入同路径，不覆盖现有成品。
3. 用户未要求增强时选择 `preserve`：不拉伸、不调色、不加滤镜、不降噪、不锐化、不镜像、不变速。
4. 用户要求增强时逐项开启 `composition`、`mirror`、`color`、`filter`、`denoise`、`sharpen`、`speed`，不得折叠成不可审查的长命令。
5. 将 `stretch`、大区域修复和强增强标记为 high risk；先预览并取得明确审批。
6. 对不确定的废片段选择保留并标记复核；不得只凭模糊、静音或静帧单一证据自动删除。
7. 变速必须同时处理 video PTS 与 audio tempo，并通过 A/V sync verification；不得用 `-shortest` 掩盖偏差。
8. 工作流完成后必须清理中间文件（`*.analysis.json`、`*.plan.json`、`*.execution.json`、`duplicates.json`），只保留最终交付物（翻新视频、文案等用户需要的产出）。
9. 使用顶部对齐 3:4 裁切前必须运行内容预判，交付筛选清单、红线预览和排期；用户批准前不得执行。
10. 生成内容命名和发布文案前必须观看每个视频的代表帧（至少开头/中段/结尾）；不得从原文件名、拆分标签或账号主题反推画面内容。文案表中的文件名必须与实际输出逐一核验。
11. 必须先生成并审阅 `视觉核验映射.tsv`：每个输出段落都要有 `状态=exact` 或人工确认的 `reviewed_category`；仍为 `category_only`、空值或仅序号的条目一律进入 HOLD，不得生成“可发布”文案或最终命名。执行前后强制校验文件名、映射表、文案表三方一一对应；发现不一致立即停止，不得交付半成品。
12. 最终发布文案使用可读 `.txt`：每个视频单独一份，子目录与批次根目录各有汇总；中文与 English 分区表达，保留原始英文文案。机器 JSON/TSV 仅作为审批或内部证据，不得替代人类交付物。
13. 下载后的输入必须先做 QuickTime 兼容性预检：VP9/VP09、非 H.264、非 AAC 或非 MP4 容器先运行 `normalize`，生成新 H.264 + AAC MP4；转换通过 `ffprobe` 和完整解码验证后，才进入 `dedupe`、`analyze` 或翻新。

## 选择工作流

- 只要分析报告：运行 `analyze`，不要运行 `apply`。
- 要处理刚下载的 MP4：先运行 `normalize`；VP9/VP09 会转为 H.264 + AAC MP4，源文件不动。
- 要找重复素材：运行 `dedupe`；默认只报告，不删除文件。
- 要找转码、裁切或轻微编辑后的相似素材：运行 `fingerprint`；输出跨时间采样的候选组与置信度，仅供本地人工复核。
- 要规范化非内容元数据：先 `normalize`，再运行 `metadata` 输出新 MP4；完成后重新运行 `fingerprint`。
- 要拆分多主题长视频：先运行 `split_multitheme_video.py` 生成分析 JSON 和中点联系表；观看预览、核对边界及逐段命名后，才带审批参数执行。
- 要清理或翻新：先 `analyze`，再用用户意图生成 `plan`，展示关键操作、风险、预览要求与输出路径。
- 要执行：核对计划、源文件哈希、preview approval、conflict approval 和所有 high-risk approval；只执行当前明确支持的类型化操作。
- 要验证已有输出：运行 `verify`，输出结构化 verification report。
- 要下载社交平台素材：改用 `safe-instagram-social-archiver`；本 Skill 不维护登录态、cookie 或下载器。

## 运行 CLI

先确认 `python3`、`ffmpeg` 和 `ffprobe` 可用。将 `SKILL_DIR` 设为本 Skill 目录，再运行：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" analyze INPUT --source generic --report analysis.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" normalize INPUT.mp4 \
  --output INPUT__h264-aac.mp4 --report normalize.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" dedupe INPUT_DIR --report duplicates.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" fingerprint INPUT_DIR --threshold 0.86 --report perceptual-dedupe.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" metadata INPUT.mp4 --output OUTPUT__catalog-clean.mp4 --report metadata.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" plan INPUT --analysis analysis.json \
  --accept-suggested-tail --final-output OUTPUT.mp4 --output plan.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" apply plan.json --report execution.json
python3 "$SKILL_DIR/scripts/video_pipeline.py" verify plan.json --report verification.json
```

需要机器输出时加 `--json`。先运行对应子命令的 `--help` 查看类型化选项。

下载后先做兼容化（即使已经是 H.264/AAC，也会生成经过验证的新 MP4；若无需重编码则使用安全 remux）：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" normalize DOWNLOADED.mp4 \
  --output "DOWNLOADED__h264-aac.mp4" \
  --report normalize.json
```

报告中的 `status` 为 `converted` 或 `already_compatible`；只有 `verified=true` 才能把新文件交给后续流程。VP9/VP09 会使用 `libx264 + yuv420p`，音频统一写为 AAC，容器统一为 MP4，并启用 `+faststart`。

多主题拼接视频先分析、不立即切割。两种方法按素材特征选择：

**内容感知法（默认首选）** — `content_split.py`，直接从 ffmpeg scene scores 做峰值检测，不预设固定节拍。适合段长不规则的拼接视频（如不同长度的剪辑片段拼成）：

```bash
# 1) 分析 + 预览
python3 "$SKILL_DIR/scripts/content_split.py" --input-dir INPUT_DIR \
  --output-dir PREVIEW_DIR --analyze --preview

# 2) 审核预览帧和 _content_summary.tsv 后执行
python3 "$SKILL_DIR/scripts/content_split.py" --input-dir INPUT_DIR \
  --analysis-dir PREVIEW_DIR --execute --output-dir OUTPUT_DIR
```

**自适应策略**（已内置，无需手动调参）：
- Pass 1：min_height=0.25、min_distance=2.5s 找高置信切点
- Pass 2：对 >15s 的长段，降阈值到 0.10 重扫全部原始峰，逐个测试找最佳平衡切点；同时启动 dHash 滑动窗口备援（弥补 ffmpeg scene detection 对同场景过渡的盲区）
- build_segments 返回 `(segs, merged)`，merged=True 时拒绝该切点（避免生成碎片后被合并消掉）
- Pass 3：过拆分检查——中位段 <7s 时合并最差切点

**诊断经验**：4 类问题模式
1. **过度拆分**：中位段 <7s → Pass 3 自动合并
2. **密集峰合并**：多个高峰挤在 5s 窗口内 → Pass 2 逐个原始峰测试，不依赖聚类
3. **转场不可检测**：同场景同光线，ffmpeg scene score <0.15 → dHash 备援
4. **阈值过高漏切**：长段 >20s 但峰分 <0.25 → Pass 2 降阈值到 0.10 全覆盖

**节拍法（备选）** — `split_multitheme_video.py`，适合段长均匀（约 10s / 15s 等距）的拼接视频：

```bash
python3 "$SKILL_DIR/scripts/split_multitheme_video.py" INPUT \
  --analysis split-analysis.json \
  --preview split-preview.jpg
```

必须观看联系表，核对切点、段数和片尾排除范围。确认后执行：

```bash
python3 "$SKILL_DIR/scripts/split_multitheme_video.py" INPUT \
  --analysis split-analysis.json \
  --preview split-preview.jpg \
  --execute --approve-review \
  --names-map names.tsv \
  --output-dir OUTPUT_DIR
```

**选择指南**：先用内容感知法分析两个样本——若段长差异>30%说明节拍法不适用。若段长均匀（±15%），任选其一。

执行统一用精确时间线重编码（trim/atrim + setpts/asetpts），逐段完整解码验证，输出 `拆分清单.tsv`。不得仅按整数秒盲切；弱转场、黑屏范围、段数或命名不确定时保持分析状态，先人工复核。源文件不动，输出目录不得已存在。

保真计划保持所有增强关闭。可控增强示例：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" plan INPUT \
  --composition fit --resolution 1080x1920 \
  --mirror \
  --color natural --filter cinematic \
  --denoise light --sharpen light --speed 1.06 \
  --approve-preview --approve-conflicts \
  --final-output OUTPUT.mp4 \
  --output plan.json
```

**逐视频精准自由裁剪（文字标签与 Logo 定位）**：

先运行 `smart_label_detect.py`。工具以低分辨率时序共识和二维网格确定候选框，映射回原始坐标后比较上下左右四种裁法，输出内容损失最小的裁剪候选；它不直接修改视频。

```bash
# 单视频分析
python3 "$SKILL_DIR/scripts/smart_label_detect.py" VIDEO.mp4 \
  --creator CREATOR_NAME --memory MEMORY_DIR \
  --target-label magicbox.studio \
  --report label-crop-analysis.json --preview-dir previews

# 批量分析；人工确认后才另行写入创作者记忆
python3 "$SKILL_DIR/scripts/smart_label_detect.py" --input-dir DIR \
  --creator CREATOR_NAME --memory MEMORY_DIR \
  --target-label magicbox.studio \
  --output-dir ANALYSIS_DIR --preview-dir ANALYSIS_DIR/previews
```

必须审查红色候选框和绿色保留框。`review_required=true`、组合内容损失超过 20%、候选不贴边或框到主体时一律 HOLD。只有人工确认后才可加入 `--confirm-memory` 写入创作者记忆。完整算法、输出和执行门禁见 [references/label-logo-detection.md](references/label-logo-detection.md)。

将 9:16 裁成 3:4 并从底部排除右下水印（固定比例，标签位置统一时用）：

```bash
python3 "$SKILL_DIR/scripts/crop_3x4_preflight.py" INPUT_DIR \
  --output-dir PREFLIGHT_DIR --start-date 2026-07-23 --per-day 10
```

先审查 `crop_3x4_screening_schedule.tsv` 和 `previews/`：

- `适合`：底部裁除带内容风险较低，可进入第一批。
- `人工复核`：检查车轮、手部、字幕和主体是否越过红线。
- `不适合`：保持 HOLD，改用轻度放大、固定区域修复或保留原画幅。

用户批准具体清单后，才为入选视频生成：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" plan INPUT \
  --crop-aspect 3:4 --crop-anchor top \
  --composition preserve --resolution 1080x1440 \
  --quality hd --approve-preview \
  --final-output OUTPUT.mp4 --output plan.json
```

轻度放大并保留左上主体，从右侧和底部排除固定水印：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" plan INPUT \
  --safe-zoom 1.08 --zoom-anchor top-left \
  --composition fit --resolution 1080x1920 \
  --quality hd --approve-preview \
  --final-output OUTPUT.mp4 --output plan.json
```

先计算水印到边缘的距离，再选择最小可行 zoom。`1.01–1.15` 为中风险，超过 `1.15` 为 high risk；不得为了去水印盲目放大导致主体或字幕被裁。

使用 `--mirror` 执行水平镜像，或使用 `--flip horizontal|vertical|both` 明确反转方向。水平镜像必须预览；`vertical` 和 `both` 属于 high risk。不得为了素材“去重”自动镜像。

用户明确要求非等比缩放时才使用 `--composition stretch`。只有用户已经看过预览并批准，才加入 `--approve-high-risk`。

处理获授权的固定区域时，先要求用户确认区域，再写入计划：

```bash
python3 "$SKILL_DIR/scripts/video_pipeline.py" plan INPUT \
  --remove-region '78%:78%:20%:18%' \
  --confirm-authorized-removal --approve-preview \
  --final-output OUTPUT.mp4 --output plan.json
```

不要对移动水印或大面积复杂背景连续堆叠 `delogo`；改为读取 removal backend 参考并路由到 VSR。

## 审查计划

在交付或执行前检查：

- `input.sha256` 是否仍匹配源文件。
- `operations` 是否逐项反映用户意图；`mode=auto` 是否已经展开为确定参数。
- `conflict_checks` 是否存在 `needs_review`，尤其同时启用 `color` 与 `filter` 时。
- `preview.required` 是否与中高风险操作一致。
- 所有 `risk=high` 操作是否 `approved=true`。
- `output.path` 是否与输入不同且不存在覆盖风险。
- `plan_hash` 是否有效。

## 资源路由

- 需要跨 macOS、Linux、Windows 安装依赖，或安装到 Codex、Claude Code、其他 Agent 时，读取 [references/installation-and-agents.md](references/installation-and-agents.md)。
- 需要升级本机已安装的多个 Agent 时，先更新仓库，再运行 `scripts/install_skill.py --sync-agents`；不要直接编辑某个 Agent 的复制目录。
- 需要批量操作、命名、文案、清理与验收的经验门禁时，读取 [references/avoid-pitfalls.md](references/avoid-pitfalls.md)。
- 需要完整阶段、状态、输出布局和 review gate 时，读取 [references/workflow.md](references/workflow.md)。
- 需要 3:4 预判、构图、镜像反转、调色、滤镜、降噪、锐化、变速的模式、顺序或风险时，读取 [references/transform-options.md](references/transform-options.md)。
- 需要抖音、TikTok、Instagram Reels、YouTube Shorts 的分析差异时，读取 [references/platform-profiles.md](references/platform-profiles.md)。
- 需要选择 `delogo`、`removelogo` 或 VSR 后端时，读取 [references/removal-backends.md](references/removal-backends.md)。
- 需要定位文字标签、Logo 或生成最小损失裁剪候选时，读取 [references/label-logo-detection.md](references/label-logo-detection.md)。
- 需要实现或校验计划结构时，读取 [references/plan.schema.json](references/plan.schema.json)。

## 交付与清理

执行完成并确认汇总报告后再清理。先写报告，再将中间物移入批次归档或系统废纸篓；不要使用不可恢复删除。

- 只保留用户需要的最终交付物：翻新后的视频（`.mp4`）、中英分区发布文案（`.txt`）、视觉核验映射与处理报告等
- 源文件始终不动
- 清理前确认所有 `apply` 状态为 `verified`

**实战踩坑**：多次遗漏 `preview_frames/` 和 3:4 preflight 目录，用户提醒后才补清。这两个目录在源目录下而非输出目录，容易被忽略。交付后对照 [避坑指南](references/avoid-pitfalls.md) 的清理清单逐项移入批次归档或系统废纸篓。

## 阶段边界

当前版本已实现：下载后 VP9/VP09 → H.264 + AAC MP4 兼容化、媒体探测、精确哈希与基础感知指纹去重、相似候选组和置信度报告、非内容元数据规范化、多证据废片尾分析、10/15 秒节奏候选比较、多主题真实转场定位、黑尾排除、分段联系表、逐段命名与完整解码验证、文字标签/Logo 二维候选定位与最小损失裁剪建议、3:4 批量预判与红线预览、筛选清单与排期、显式裁切审批、固定区域 `delogo`、3:4 锚点裁切、1.0–1.25 倍安全放大、Lanczos 高清缩放、HD/HD+ 编码、水印后端路由元数据、`fit/fill/stretch` 构图、水平/垂直镜像、预设调色与滤镜、降噪、锐化、音画同步变速、临时输出验证和无覆盖交付。

不要声称已经实现：`smart/manual` 内容感知构图、移动水印跟踪、通用视频 inpainting、Gemini remover 实际执行、内置 VSR 模型、OCR 字幕重建或批处理续跑。感知指纹仅用于本地分类/人工复核，不修改或伪造指纹，也不用于规避平台规则。`auto` 只能形成建议，必须展开为确定参数后才能执行；custom filter graph 暂不开放执行。
