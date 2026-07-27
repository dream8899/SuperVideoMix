# SuperVideoMix Skill 需求文档

- Skill 产品名：`SuperVideoMix`
- Skill 机器名：`super-video-mix`
- 项目代号：`SuperVideoMix`
- 文档状态：Draft v0.6（Core MVP 实施基线）
- 当前实施状态：Core MVP ready for installation（2026-07-20）
- 目标形态：一个 Skill、一个统一 CLI、多个内部模块

## 1. 决策摘要

SuperVideoMix 应将“保守清理”和“可控翻新”整合为同一条短视频后期任务链，但不应将所有 FFmpeg 参数堆进一个巨型脚本。

采用以下原则：

1. 先分析，再生成计划，最后显式执行。
2. 清理和翻新是两个独立阶段，可分别开关。
3. “去重”必须分为素材去重、重复帧治理和合法的内容重新编排，不得宣称规避平台重复内容检测。
4. 默认不覆盖原视频，默认不做镜像、强制调色、强制变速或加字。
5. 每个输入必须生成可审查的 JSON 计划、处理清单和验证结果。
6. 下载层与媒体处理层保持分离；社交平台下载继续交给 `safe-instagram-social-archiver`。
7. Skill 指令与人类摘要以中文为主；CLI、JSON schema、枚举、错误码、FFmpeg 术语和关键技术接口保留英文。
8. “原样保真”和“可控增强”使用同一套类型化操作表示：默认可全部关闭，也必须支持逐项开启、预设、自动建议和自定义参数，包括明确选择的镜像反转。

### 1.1 语言与接口约定

- `SKILL.md`、工作流说明、风险提示和给用户的结论使用中文。
- frontmatter `description` 使用中文说明能力，同时保留 `analyze`、`deduplicate`、`clean`、`transform`、`verify` 等英文触发词。
- CLI command、option、JSON field、enum、job state、error code 和 FFmpeg filter 名保持英文，避免机器接口因本地化发生漂移。
- 结构化输出中的 `status`、`mode`、`risk` 等值使用稳定英文枚举；旁边可提供中文 `summary` 或 `message`。
- 关键执行门使用明确英文名，例如 `review gate`、`dry-run`、`plan hash`、`high-risk approval` 和 `A/V sync verification`。

## 2. 背景与问题

现有能力分散在两处：

- `ffmpeg_video_cut`：提供裁切、调色、锐化、降噪、镜像、变速、加字和编码，但参数全部硬编码，缺少分析、规划、音画同步保护、失败检查和输出验证。
- `smart-short-video-cleaner`：提供废片尾分析、黑屏/静音/静帧/低细节证据、区域修复、掩膜和 VSR 后端，但不负责完整的素材去重、可控翻新、输出规格管理和批处理恢复。

当前的主要风险：

- 将轻微裁切、镜像或调色误称为“去重”。
- 强制 60 fps 为低帧率素材制造重复帧。
- 只修改视频 PTS，不同步处理音频，导致音画错位。
- 强制拉伸到 1080×1920，伤害非 9:16 画面。
- 使用固定 20 Mbps、固定镜像、固定文字和固定滤镜，缺少用户意图。
- 批处理无输入过滤、无断点续跑、无重复跳过、无逐文件报告。

## 3. 真实用户任务

### 3.1 核心任务

用户希望对自有或获授权的短视频完成：

1. 识别已下载、已处理或高度相似的素材，避免重复加工。
2. 找出废片尾、黑屏、静帧、重复帧、空镜和明显异常段。
3. 在授权范围内处理固定水印、硬字幕或需要重新排版的文字区域。
4. 根据内容和目标比例重新构图，而不是简单拉伸。
5. 可选地调色、加滤镜、降噪、锐化、同步变速、叠加自有品牌文字或字幕。
6. 导出符合目标用途的视频，并验证时长、音画、分辨率、帧率、编码和完整性。
7. 对文件夹批量执行，可暂停、续跑、跳过已完成项并定位失败项。

### 3.2 典型请求

- “先分析这个抖音视频，告诉我片尾和异常段，不要修改。”
- “清掉黑屏片尾，再转成 9:16，不要镜像。”
- “这个文件夹里哪些是重复素材？先给清单。”
- “把自有横屏视频重新构图为 Shorts，保留人物和字幕安全区。”
- “把底部硬字幕清理后重新加可编辑字幕，先做 10 秒预览。”
- “批量处理这 100 个视频，失败的留在报告里，不要从头重跑。”

## 4. 术语与边界

### 4.1 素材去重

目标是识别相同或高度相似的输入，避免重复存储、重复编码和重复人工复核。

必须支持：

- 完全相同：SHA-256、文件大小和容器基本信息。
- 视听内容相似：分段采样帧指纹、时长差、分辨率、音频特征和置信度。
- 已处理检测：输入哈希 + 计划哈希 + 工具版本。

不得使用“去重”表示通过画面扰动规避平台规则。

### 4.2 重复帧与静帧段

- 重复帧：编码、帧率转换或源素材引入的连续近似帧。
- 静帧段：画面静止但可能仍然是正常叙事，不能仅凭画面不动自动删除。
- 治理必须同时考虑音频、持续时长、位置和相邻内容。

### 4.3 清理

从已有视频中去除有充分证据的无效段或处理获授权的画面元素，应优先保留内容。

### 4.4 翻新与重新编排

对自有或获授权内容进行有明确意图的编辑，例如重新构图、叙事裁切、字幕重建、品牌包装、调色和音频优化。镜像、裁掉 1% 或轻微调色不得被表述为原创性保证。

## 5. 产品目标

### 5.1 P0：首个可用版本

1. 统一分析：容器、视频、音频、时长、帧率、旋转、画幅比和可解码性。
2. 下载兼容化：检测 VP9/VP09、非 H.264、非 AAC 或非 MP4 输入，先生成经过完整解码验证的 H.264 + AAC MP4；源文件不覆盖。
3. 素材去重：精确哈希、基础感知指纹、相似候选组和置信度。
4. 废片尾分析：复用已验证的黑屏、静音、低纹理、静帧和重复证据。
5. 保守清理：精确裁尾、固定区域 `delogo`、掩膜 `removelogo`、可选 VSR 适配。
6. 基础翻新：显式裁切、无拉伸缩放/填充、可选调色、滤镜、降噪、锐化、镜像和同步变速。
7. 输出编码：H.264/AAC、CRF 质量模式、帧率默认保留、分辨率默认保留。
8. 计划与执行分离：`normalize`/`analyze`/`plan` 不覆盖输入，`apply` 只执行已保存计划。
9. 批处理：扩展名过滤、逐文件计划、状态持久化、断点续跑和失败清单。
10. 输出验证：文件存在、可解码、视频轨、音频轨、时长、画面尺寸、帧率和计划一致性。

### 5.2 P1：增强版本

- 内容感知的 9:16 重新构图，优先保留人脸、主体和文字安全区。
- 更完整的视频感知指纹和相似度聚类。
- 片头、中插空镜、异常卡帧和镜头边界分析。
- 可编辑字幕重建：检测、OCR、时间轴、样式和重绘。
- 音频响度、削波、底噪和音画偏移检测。
- 预览片段和前后对比图。

### 5.3 P2：高级版本

- 跨帧移动水印检测与掩膜跟踪。
- 本地 AI 修复后端统一接口和模型能力探测。
- 多片段叙事重排、自动摘要和候选版本生成。
- 可视化复核面板、时间轴区间编辑和批量审批。

## 6. 非目标

P0 不实现：

- 不负责登录社交平台或维护账号凭证。
- 不内置 Instagram/TikTok/YouTube 下载逻辑。
- 不保证“过平台原创检测”、“防限流”或“消除版权风险”。
- 不删除 SynthID 等不可见/隐写水印。
- 不默认移除归属信息或他人品牌标识。
- 不默认对整部视频进行 AI 语义重剪。
- 不以轻微镜像、调色、裁边或修改元数据冒充原创创作。

## 7. 用户与权限模型

### 7.1 用户前提

处理破坏性操作前，Skill 必须确认：

- 用户指定输入文件或明确的输入目录。
- 用户对内容拥有编辑权或获得授权。
- 输出位置明确，且不与源文件相同。
- 需要去除的水印/字幕区域由用户指定或经预览确认。

### 7.2 默认权限

- `analyze`、`plan`、`dedupe`、`verify`：只读输入，可写报告。
- `apply`、`batch --apply`：新建输出视频，不覆盖源文件。
- 删除原文件、覆盖输出、替换已有成品：不在默认范围内。

## 8. 目标工作流

```text
Input discovery
  → Codec compatibility normalization (VP9/VP09 → H.264/AAC/MP4)
  → Probe and decode check
  → Exact/perceptual dedupe
  → Content analysis
  → JSON plan
  → Human/agent review gate
  → Clean
  → Transform
  → Encode
  → Verify
  → Manifest and batch ledger
```

### 8.1 分析阶段

输出必须包含：

- 媒体基本信息。
- 解码异常、音轨/视轨缺失和时长不可确定问题。
- 素材重复候选和置信度。
- 可疑废片段的开始、结束、证据、置信度和保留/删除建议。
- 可疑水印/字幕区域的坐标来源（用户指定、掩膜或检测器）。
- 输出规格建议和所有不确定性。

### 8.2 计划阶段

计划必须是稳定、可重放、可哈希的 JSON，不应只存储一条未结构化 FFmpeg 命令。

计划必须明确：

- 输入文件标识。
- 分析器和工具版本。
- 启用的清理步骤。
- 启用的变换步骤及顺序。
- 编码目标。
- 输出路径。
- 需要审批的高风险操作。
- 预期时长、分辨率、帧率和音轨。

每个可选变换使用同一种选择模型：

```json
{
  "type": "color",
  "mode": "off",
  "preset": null,
  "params": {},
  "risk": "low",
  "requires_preview": false,
  "approved": false
}
```

- `mode=off`：明确不执行，是保真路径的默认选择。
- `mode=auto`：分析器只生成建议参数；进入 `apply` 前必须固化成可重放参数，执行时不得重新决策。
- `mode=preset`：使用版本化预设并把展开后的具体参数写入计划。
- `mode=custom`：保存用户给出的类型化参数并通过边界校验。
- 高风险操作即使已选择也必须单独满足 `approved=true`；`auto` 不得绕过审批门。

### 8.3 执行阶段

- 只接受结构合法的计划。
- 执行前再次核对输入哈希，防止源文件已变更。
- 使用临时输出，验证成功后再移交到最终路径。
- 任一步骤失败时保留错误上下文，不将部分文件标记为成功。
- 不因单个批处理项失败而丢失其他项的状态。

### 8.4 验证阶段

至少检查：

- 容器可打开且可读到末帧。
- 存在预期的视频轨和音频轨。
- 实际时长在计划容差内。
- 分辨率、旋转、画幅比、帧率和编码符合计划。
- 无非预期的无声、黑屏、截断或时长突变。
- 变速后音频和视频时长一致。
- 输出哈希、计划哈希和验证结果写入 manifest。

## 9. 功能需求

### FR-01 媒体探测

- 使用 `ffprobe` JSON 作为基础数据源。
- 保留原始时基、平均帧率和实时帧率信息，不仅保留一个浮点数。
- 识别可变帧率、旋转元数据和异常起始 PTS。
- 对不可解码文件返回非零状态和可机读错误。

### FR-02 素材去重

- 使用分块 SHA-256 避免将整个大文件读入内存。
- 感知指纹必须跨时间采样，不得只比较首帧或封面。
- 输出 `exact` / `likely` / `possible` / `distinct` 类别、数值相似度和证据。
- 默认不删除重复文件，只生成组和建议保留项。
- 保留所有指纹版本，便于算法升级后重算。

### FR-03 废片段分析

- 支持黑屏、低对比度、低细节、近似静帧、静音和连续性证据。
- 黑屏可作为强证据；静帧、模糊、低纹理和静音不得单独触发删除。
- 平台预设只调整扫描窗口和阈值，不按平台固定减秒。
- 对每个建议区间输出证据、分数、最小持续时间和边界保护。

### FR-04 水印与硬字幕处理

- 固定小区域：FFmpeg `delogo`。
- 已知掩膜：FFmpeg `removelogo`。
- 复杂字幕/运动背景：VSR 适配器，模型与依赖显式安装。
- 所有区域使用原分辨率像素坐标存储，同时可保留归一化坐标。
- 多大区域或多位置 `delogo` 必须标记高风险并生成预览。
- 不得将 Gemini 固定 Alpha 模板算法泛化到任意平台水印。

### FR-05 裁切与时间轴

- 所有裁切应使用秒和原始时基记录，不只记录帧号。
- 视频与音频必须应用对齐的 `trim`/`atrim` 区间并重置时间戳。
- 多片段保留应生成明确 concat 图，而不是依赖 `-shortest` 隐式截断。
- 对切点加入可配置的边界保护，默认宁可多保留。

### FR-06 画面变换

每项变换必须可独立关闭和独立配置。默认保真计划为：不拉伸、不调色、不加滤镜、不降噪、不锐化、不镜像、不变速，分辨率与帧率保持原样。

- `composition.mode=preserve|fit|fill|smart|stretch|manual`。
  - `preserve` 保持源画布。
  - `fit` 等比完整保留画面，可补边。
  - `fill` 等比铺满，允许经计划确认的裁切。
  - `smart` 为 P1 内容感知重新构图；P0 只能保存建议或显式坐标。
  - `stretch` 允许非等比缩放，但必须标记 `risk=high`、生成预览并显式审批，不能成为任何预设默认值。
- `resolution=preserve|WIDTHxHEIGHT`。
- `fps=preserve|VALUE`。
- `mirror.mode=off|horizontal|vertical|both`。
  - `horizontal` 使用 FFmpeg `hflip`，即常用的左右镜像。
  - `vertical` 使用 FFmpeg `vflip`，即上下反转。
  - `both` 使用 `hflip,vflip`，视觉上等价于旋转 180°；不等同于单纯水平镜像。
  - 水平镜像标记 `risk=medium` 并要求预览；垂直或双向反转标记 `risk=high` 并要求显式审批。
- `denoise.mode=off|auto|preset|custom`，预设至少包含 `light` / `medium`。
- `sharpen.mode=off|auto|preset|custom`，预设至少包含 `light` / `medium`。
- `color.mode=off|auto|preset|custom`，预设至少包含 `natural` / `warm` / `vivid`。
- `filter.mode=off|preset|custom`；预设必须版本化，自定义 FFmpeg filter graph 必须作为单个参数传递、禁止 shell 拼接并经过 allowlist/denylist 与范围检查。
- `overlay-text`/`overlay-image`：只能使用用户提供内容，不得内置品牌文字。

规则：

- 非等比缩放只能通过显式 `stretch` 选择进入计划，并经预览和确认。
- 不为了“去重”自动镜像、加噪或扰动颜色。
- 镜像反转只在用户明确要求或编辑意图确实需要时启用；不得用于掩盖来源或宣称原创。
- 不默认将低帧率源素材升到 60 fps。
- 调色应使用可读参数结构，不接受无来源的长滤镜字符作为产品预设。
- `auto` 只负责提出建议；`apply` 只能执行计划中已经展开并固定的参数。
- 同时启用 `color` 和 `filter` 时必须执行冲突检查，避免重复调整曝光、对比度、饱和度或色温。
- 处理顺序固定为：时间轴裁切/变速与 PTS 重建 → 区域清理 → 重新构图/缩放 → 降噪 → 调色/滤镜 → 锐化 → 文字/图像叠加 → 帧率/像素格式/编码。
- 中高强度调色、滤镜、降噪、锐化以及任何 `stretch` 必须先生成短预览；批处理必须先用代表性样本确认。

### FR-07 同步变速

- `speed.mode=off|preset|custom`；`off` 等价于 `factor=1.0`，预设展开为明确数值，自定义必须限制在已定义安全范围内。
- 视频使用精确 `setpts` 表达式。
- 音频使用 `atempo` 链与视频速度对齐。
- 当速度超出单个 `atempo` 支持范围时自动拆分链。
- 变速后的音视频时长差必须在容差内，不得使用 `-shortest` 掩盖错位。
- `speed` 与裁切都属于时间域操作，必须在计划中明确先后关系；默认先裁切保留区间，再同步变速。

### FR-08 输出编码

P0 至少支持：

- H.264 + AAC + MP4。
- 下载后若检测到 VP9/VP09 或 QuickTime 不兼容编码，必须先走 `normalize`，成功验证后再进入查重和翻新。
- CRF 质量模式，默认不使用固定 20 Mbps。
- `faststart`。
- 帧率、分辨率、像素格式和音频采样率的显式计划。
- 对无音轨输入不人工生成空音轨，除非用户需要。
- 保留原旋转语义，或在旋转像素后正确清理旋转元数据。

### FR-09 批处理与状态

- 只接受明确支持的视频扩展名或解码检查通过的文件。
- 每个输入使用独立 job ID、报告、计划、日志和输出。
- 状态至少包含 `discovered` / `analyzed` / `planned` / `running` / `verified` / `failed` / `skipped_duplicate`。
- 续跑时核对输入和计划哈希，不仅根据输出文件是否存在。
- 支持 `--dry-run`、`--continue-on-error`和可控并发度。

### FR-10 验证与比较

- 输出结构化 `verification` 对象，而不仅输出文本日志。
- 比较输入和输出的时长、轨道、尺寸、帧率、容器、编码和解码状态。
- 当实际变化超出计划容差时将 job 标记为失败或需复核。
- 输出可选预览截图和短片段，但不默认导出大量中间文件。

## 10. 统一 CLI 需求

候选入口：

```bash
python3 scripts/video_pipeline.py COMMAND [OPTIONS]
```

P0 子命令：

```bash
# 分析单个视频，不渲染
video_pipeline.py analyze INPUT --source douyin --report analysis.json

# 比较目录内素材，不删除
video_pipeline.py dedupe INPUT_DIR --report duplicates.json

# 根据分析与用户意图生成稳定计划
video_pipeline.py plan INPUT --analysis analysis.json --preset vertical-social --output plan.json

# 保真路径：不拉伸、不增强、不变速
video_pipeline.py plan INPUT --preset preserve --composition preserve --color off --filter off --denoise off --sharpen off --speed 1.0 --output plan.json

# 可控增强路径：逐项开启，仍先生成计划
video_pipeline.py plan INPUT --composition fit --resolution 1080x1920 --color natural --filter cinematic --denoise light --sharpen light --speed 1.06 --output plan.json

# 水平镜像快捷参数；也可使用 --flip horizontal
video_pipeline.py plan INPUT --mirror --output plan.json

# 上下或双向反转属于高风险，需要预览后审批
video_pipeline.py plan INPUT --flip vertical --approve-high-risk --output plan.json

# 执行一个已审查计划
video_pipeline.py apply plan.json

# 验证已有输出
video_pipeline.py verify plan.json --report verification.json

# 批处理，默认 dry-run
video_pipeline.py batch INPUT_DIR --preset vertical-social --workspace JOB_DIR --dry-run
```

CLI 通用规则：

- 参数错误、工具缺失、输入错误、执行失败和验证失败使用不同的非零退出码。
- `--json` 模式下 stdout 只输出机读结果，人类日志写入 stderr。
- 命令应可安全重跑。
- 默认不使用 `-y`；已有输出返回明确状态。
- 输出路径必须在执行前完全解析并写入计划。

## 11. JSON 计划模型

P0 计划至少包含：

```json
{
  "schema_version": "1.0",
  "job_id": "stable-id",
  "created_at": "ISO-8601",
  "input": {
    "path": "/absolute/input.mp4",
    "sha256": "...",
    "duration": 30.12,
    "width": 1080,
    "height": 1920,
    "fps": "30000/1001",
    "has_audio": true
  },
  "analysis": {
    "profile": "douyin",
    "duplicate_group": null,
    "suggested_intervals": [],
    "uncertainties": []
  },
  "operations": [
    {
      "type": "trim",
      "start": 0.0,
      "end": 27.8,
      "evidence": ["dark", "silent"],
      "approved": true
    },
    {
      "type": "reframe",
      "mode": "fit",
      "width": 1080,
      "height": 1920,
      "approved": true
    }
  ],
  "encode": {
    "container": "mp4",
    "video_codec": "libx264",
    "crf": 18,
    "fps": "preserve",
    "audio_codec": "aac",
    "audio_bitrate": "192k"
  },
  "output": {
    "path": "/absolute/output.mp4",
    "overwrite": false
  },
  "tool_versions": {},
  "plan_hash": "..."
}
```

规则：

- `plan_hash` 使用排除自身字段后的标准化 JSON 计算。
- 所有路径使用绝对路径。
- 操作顺序是语义的一部分，执行器不得随意重排。
- 高风险操作必须有 `approved=true`。
- 计划模型升级必须通过 `schema_version` 管理。

## 12. 内部架构需求

推荐的 Skill 目录：

```text
super-video-mix/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── video_pipeline.py
│   └── videoremix/
│       ├── analyzer.py
│       ├── cli.py
│       ├── constants.py
│       ├── errors.py
│       ├── executor.py
│       ├── io_utils.py
│       ├── media.py
│       └── plans.py
└── references/
    ├── workflow.md
    ├── platform-profiles.md
    ├── transform-options.md
    └── removal-backends.md
```

架构约束：

- `SKILL.md` 只保留工作流、决策树、安全门和资源路由，不复制完整 CLI 文档。
- 平台预设、变换选项和后端对比放在一级 `references/`。
- 命令构建使用参数列表，不使用 shell 拼接。
- 基础实现仅依赖 Python 标准库、FFmpeg 和 ffprobe；AI/OCR 后端作为显式可选依赖。
- 不在 Skill 包中包含大模型权重。

## 13. Skill 触发与行为

### 13.1 候选 frontmatter

```yaml
---
name: super-video-mix
description: 面向抖音、TikTok、Instagram Reels、YouTube Shorts 等授权短视频，执行素材去重、废片尾分析与清理、固定水印或硬字幕区域处理、重新构图、镜像反转、调色、滤镜、降噪、锐化、音画同步变速和输出验证。Use when Codex needs to analyze, deduplicate, clean, mirror or flip, transform, or verify authorized short-form videos with reviewable JSON plans and without overwriting source files.
---
```

### 13.2 Skill 必须遵循的决策树

1. 用户只要报告：运行 `analyze` / `dedupe` / `verify`，不运行 `apply`。
2. 用户要清理：先分析，再生成计划，最后显式执行。
3. 用户要翻新：要求或推导目标画幅、风格和输出用途；不默认开启高影响变换。
4. 用户说“去重”：先区分素材查重、重复帧治理或内容重新编排。
5. 用户要去水印/字幕：确认授权和区域，按复杂度选择 FFmpeg、掩膜或 VSR。
6. 用户要批处理：先对代表性样本预览，再运行干跑，最后续跑式执行。
7. 用户未要求增强：生成 `preserve` 计划，所有可选增强保持 `off`。
8. 用户要求调色、滤镜、降噪、锐化或同步变速：逐项建模并报告预期影响，不把多项增强折叠成不可审查的滤镜字符串。
9. 用户明确要求拉伸：标记高风险并生成预览；用户只说“转成 9:16”时优先建议 `fit`、`fill` 或 `smart`，不得推导为 `stretch`。

## 14. 预设需求

预设分为两层，不得混合：

### 14.1 来源分析预设

- `generic`
- `douyin`
- `tiktok`
- `instagram`
- `youtube-short`

仅影响扫描窗口、阈值和报告提示，不自动加平台水印，不固定裁减时长。

### 14.2 输出用途预设

P0 建议：

- `preserve`：尽可能保留原尺寸、帧率和音频。
- `vertical-social`：9:16 画布，等比 fit/fill 由计划明确指定。
- `preview-fast`：用于快速审查的较低成本输出，不得作为最终成品默认。

平台的最新上传规格会变化；实现具体平台导出预设前必须核对当前官方资料。

## 15. 数据与工作目录

每个 job 建议使用：

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

数据原则：

- 报告中不写入账号 cookie、token、下载请求头或其他凭证。
- 路径和原文件名可能包含隐私，对外分享报告时支持脱敏。
- 基础处理全部本地完成，不新增遥测或隐式网络请求。
- 中间文件使用 job 专属目录，不使用不受控的全局文件名。

## 16. 非功能需求

### NFR-01 安全与可逆

- 源文件只读。
- 无显式选项时不覆盖任何已有文件。
- 计划中的输出路径与任一输入相同时拒绝执行。
- 任务中断不得留下被误认为成品的半成品。

### NFR-02 确定性与可重现

- 相同输入、相同计划、相同工具版本应生成语义一致的输出。
- 记录 FFmpeg、ffprobe、Python、可选模型和 Skill 版本。
- 不在执行阶段临时重新决策参数。

### NFR-03 兼容性

- macOS Apple Silicon 为首个验收环境。
- P0 实现不依赖 shell 特性，命令执行使用 Python 参数列表。
- 后续支持 Linux；Windows 路径与字体行为单独验收。

### NFR-04 性能

- 分析优先使用低分辨率、低帧率采样，不进行全片逐帧 Python 解码。
- 精确哈希使用分块流式读取。
- 批处理并发度必须可配置，默认保守，避免同时运行过多 FFmpeg 编码任务。
- 感知指纹、分析结果和预览支持缓存，缓存键包含输入哈希与算法版本。

### NFR-05 可观测性

- 每个步骤记录开始、结束、耗时、命令摘要和退出状态。
- 不在日志中打印凭证或未脱敏外部请求。
- 对用户输出简洁摘要，详细 FFmpeg stderr 存入 job 日志。

## 17. 错误与降级

必须处理：

- FFmpeg/ffprobe 缺失。
- 编解码器不支持。
- 无视频轨、无音频轨或时长未知。
- 输入在计划后变更。
- 输出已存在。
- 磁盘空间不足。
- 字体、掩膜、VSR 入口或模型缺失。
- 分析器无法给出足够置信度。
- 渲染成功但验证失败。

降级原则：

- 检测不确定 → 保留内容，标记人工复核。
- VSR 不可用 → 不自动退回大区域 `delogo`，改为报告阻塞。
- 感知指纹失败 → 仍可输出精确哈希去重结果。
- 音频处理失败 → 不使用 `-shortest` 生成看似成功的不完整输出。
- 验证失败 → 保留临时输出供诊断，但不移交到最终成品路径。

## 18. 验收标准

### AC-01 分析不改源文件

- 执行 `analyze` 前后输入 SHA-256 一致。
- 只生成明确指定的报告或 job 文件。

### AC-02 废片尾检测

- 对“3 秒正常视听 + 2 秒黑屏静音”合成样本，建议裁点在 3.0 秒附近的一个采样周期内。
- 对“纯色画面 + 持续有声音”不建议删除。
- 对低于预设最小时长的尾段不自动建议裁切。

### AC-03 音画同步变速

- 对有音频的 1.06× 变速样本，音频与视频实际时长差不超过一个输出视频帧周期或经定义容差。
- 不通过 `-shortest` 隐藏偏差。

### AC-04 构图与分辨率

- `fit` 不裁掉源画面，不拉伸。
- `fill` 保持原画幅比，裁切区域可从计划还原。
- `preserve` 不改变源分辨率和旋转语义。
- `stretch` 未经高风险审批时必须拒绝计划执行。

### AC-04B 可选增强

- 保真计划中 `color`、`filter`、`denoise`、`sharpen` 和 `speed` 均可保持关闭，输出不得出现隐式增强。
- `mirror=horizontal`、`vertical`、`both` 必须分别生成 `hflip`、`vflip`、`hflip,vflip` 的确定计划；默认保持 `off`。
- 每项增强可独立启用；计划必须保存模式、预设版本、展开参数、风险与审批状态。
- 同时启用调色和滤镜时必须产生冲突检查结果。
- 中高强度增强必须有可定位的预览产物或明确的待预览状态。

### AC-05 素材去重

- 完全相同文件必须分到 `exact` 同一组。
- 只修改容器元数据的视频应成为高相似候选。
- 内容明显不同但时长相同的视频不得仅因时长相同分组。
- 默认不删除任何重复候选。

### AC-06 计划重放

- 相同输入与计划可在独立临时目录中重放。
- 输入被修改后，旧计划必须拒绝执行。
- 未审批的高风险操作不得执行。

### AC-07 批处理续跑

- 中途中断后，已验证成功且哈希匹配的 job 不重处理。
- 失败 job 可单独重试。
- `--continue-on-error` 下单个输入失败不阻断后续输入。

### AC-08 输出验证

- 无视频轨、不可解码、时长偏差超限或规格不匹配的输出不得标记为 `verified`。
- 验证失败的文件不移交到最终成品路径。

## 19. 测试需求

### 19.1 单元测试

- 路径安全与输出冲突。
- 分数/比率帧率解析。
- 区域像素与百分比坐标。
- 区间合并、最小时长和边界保护。
- `atempo` 链生成。
- 标准化 JSON 和 plan hash。
- job 状态迁移。
- 精确哈希与感知相似度阈值。

### 19.2 FFmpeg 集成测试

使用 `lavfi` 生成小型确定性样本：

- 正常画面 + 黑屏静音尾段。
- 纯色有声视频。
- 有音频/无音频输入。
- 横屏、竖屏、方形和旋转元数据输入。
- 固定区域 `delogo` 渲染。
- 同步变速。
- 中断输出和解码失败。

### 19.3 回归测试

- 保留一组小型授权样本的分析报告和计划快照。
- 算法阈值变更时显式审查快照差异。
- 不在 Skill 中打包未授权的社交平台视频样本。

## 20. 迁移方案

### 阶段 1：建立新骨架

- 创建 `super-video-mix` Skill 骨架和统一 CLI。
- 定义 JSON schema、退出码、job 状态和输出布局。
- 实现 `analyze`、精确哈希 `dedupe`、类型化 `plan` 和基础 `verify`，其余执行能力以明确的阶段边界返回。
- 固化中文优先的 Skill 指令与英文机器接口。
- 用单元测试覆盖 plan hash、保真默认值、可选增强和高风险 `stretch` 审批门。
- 保持现有 `smart-short-video-cleaner` 可用。

### 阶段 2：迁移清理能力

- 将已验证的 cleaner 逻辑拆入 `analyze.py` 和 `clean.py`。
- 保留现有阈值和 7 项测试，再增加 JSON schema 与执行器测试。
- 在新 Skill 稳定前不删除旧 Skill。
- 实施状态：已迁移多证据废片尾分析、显式建议审批、同步裁切、临时输出验证与无覆盖交付；固定区域清理已进入统一执行器。

### 阶段 3：重写翻新能力

- 不复制旧长滤镜字符。
- 将裁切、构图、调色、降噪、锐化、镜像、变速和叠加拆成类型化操作。
- 每个操作独立测试，组合后进行音画和时长验证。
- 实施状态：Core MVP 已支持 `fit/fill/stretch`、固定区域 `delogo`、镜像、预设调色/滤镜、降噪、锐化和同步变速；`smart/manual`、custom filter graph 与叠加操作继续后续开发。

### 阶段 4：增加去重与批处理

- 实现精确哈希、感知指纹、相似组、job ledger 和续跑。
- 先以 dry-run 和报告模式验证真实批次。

### 阶段 5：切换 Skill

- 对代表性请求进行前向测试。
- 验证新 Skill 可独立完成清理、翻新、去重、批处理和输出验证。
- 停用旧 Skill 的隐式触发，保留兼容入口一个过渡周期。
- 用户确认后再归档旧 Skill 和旧脚本，不自动删除。

## 21. 实现优先级

### P0 开发顺序

1. 数据类型、JSON schema、标准化与 plan hash。
2. `probe` 与输入安全。
3. 精确哈希去重和 job ledger。
4. 迁移 cleaner 分析与清理。
5. 类型化 transform 和同步变速。
6. 编码器与临时输出交付。
7. 验证器。
8. 感知指纹。
9. 批处理续跑。
10. Skill 封装、UI 元数据和前向测试。

## 22. 成功指标

P0 成功不以“视频变得不一样”为标准，而以以下结果衡量：

- 分析和干跑对源文件零修改。
- 处理计划可读、可审查、可哈希、可重放。
- 废片尾合成样本通过，且纯色有声样本不误删。
- 变速不造成可见音画偏移。
- 默认不拉伸画面、不强制 60 fps、不加硬编码文字。
- 相同输入与计划可被稳定跳过，失败项可单独重试。
- 只有验证通过的输出被标记为成品。

## 23. 开放问题

继续推进 P0 时需确认：

1. 感知指纹 P0 是纯标准库 dHash 采样，还是引入 OpenCV/NumPy 以提高精度？
2. job ledger 使用 SQLite 还是 JSONL？建议 P0 使用 SQLite，同时支持 JSON 导出。
3. `vertical-social` 默认使用 fit 还是 fill？建议计划必须明确，Skill 根据内容给建议但不隐式选择。
4. P0 是否纳入字幕 OCR？建议只保留 VSR 适配，OCR 重建放 P1。
5. 批处理默认并发数是 1 还是根据 CPU 探测？建议默认 1，显式参数提升。
6. 是否保留旧 `smart-short-video-cleaner` 名称作为别名？建议保留一个过渡周期，最终仅暴露 `super-video-mix`。

## 24. Definition of Done

P0 被视为完成必须同时满足：

- Skill 目录结构符合 Codex Skill 规范并通过 `quick_validate.py`。
- `agents/openai.yaml` 与 `SKILL.md` 触发范围一致。
- 所有 P0 子命令有 `--help`、结构化输出和非零错误码。
- 单元测试、FFmpeg 集成测试和代表性端到端测试通过。
- 使用至少三类代表性授权样本前向测试：只清理、只翻新、批量去重+处理。
- 无未申明网络请求、遥测、模型下载或凭证读取。
- 源文件不覆盖，输出必须验证后交付。
- 迁移指南可以将现有 cleaner 的测试和用法无损迁入新 Skill。
