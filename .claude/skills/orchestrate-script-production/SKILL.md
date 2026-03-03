---
name: orchestrate-script-production
description: 仅负责统筹并串联剧本相关子 skill 的端到端流程。关键词：编排, 流程, pipeline, orchestration, 剧本生产
---

## 功能说明

按固定流程调用子 skill，形成可落地的剧本生产流水线：
1) 与用户对话澄清需求，产出人设、剧本大纲与基础形态（视觉小说线性叙事）
2) 基于阶段1结果先生成传统小说草稿并落盘，再转换为“仅文本+演出效果”的剧本（不含背景图与人物图路径）
3) 基于阶段1结果生成人物设定图
4) 重新阅读剧本后生成背景图与人物立绘，并回写到剧本

## 生文调用约束（必须遵守）

- 阶段1（规划）与阶段2（文本剧本）涉及文本创作时，必须通过混元生文 API 生成。
- 统一调用 MCP 工具：`mcp_playwright-im_generate_text`（ChatCompletions）。
- 禁止在未调用生文 API 的情况下直接产出完整规划文本或完整剧本正文。
- 禁止要求生文 API 直接输出完整 `script.json`；生文阶段应输出传统文本草稿。
- 生文草稿必须先落盘到本地目录，再由 agent 进行 JSON 转换。
- 阶段2调用生文 API 生成 `novel_draft` 时，必须显式传入阶段1产物 `planning_draft`（建议传全文）作为上下文输入，禁止仅凭简短摘要续写。
- 长篇续写（建议 >8k token）必须使用会话复用：为阶段2连续调用传同一个 `session_id`，并启用 `use_session_history=true`。
- 当 `planning_draft` + 已生成正文片段过长时，必须改为 `context_files` 文件上下文模式：先上传文件（`FilesUploads`），再通过消息 `FileIDs` 参与对话，避免消息截断。
- 建议保持 `carry_forward_file_ids=true`（默认），确保后续批次即使未重复传 `context_files` 也会自动继承最近历史 `FileIDs`。
- 阶段2 `novel_draft` 必须采用视觉小说叙事混合写法：人物描写 + 环境描写 + 心理描写 + 对话；禁止全篇纯对话体。
- 若生文 API 调用失败，应中断后续链路并询问用户“重试 / 降级 / 终止”。

## 原创约束（必须遵守）

- 阶段1/阶段2属于文本创作阶段，禁止将项目中已有剧本正文（`scripts/*/script.json`）作为创意来源。
- 编排时仅允许子 skill 读取“当前目标剧本文件”用于续写或修订，不得读取其他剧本进行模仿、拼接或改写。
- 若用户要求参考现有剧本风格，必须改为抽象题材方向描述（如“悬疑/校园/奇幻”），不得复用现有人物设定、专有名词、关键桥段。
- 允许使用外部作品作为风格参考；当前默认参考文章为《铁道银河之夜》，但仅限主题氛围与叙事节奏借鉴，不得复述原文或复用可识别设定。

## 共享数据协议（必须遵守）

所有子 skill 必须共享同一份脚本内数据源：`scripts/<script_name>/script.json` 顶层 `shared`。

推荐结构：

```json
{
   "shared": {
      "planning": {
         "requirements_summary": "...",
         "script_form": "visual_novel",
         "planning_source": "ai_auto",
         "reference_article": {
            "title": "铁道银河之夜",
            "usage": "theme_tone_only"
         },
         "worldview": "...",
         "characters": [{ "name": "林澈", "profile": "..." }],
         "outline": [{ "chapter": 1, "summary": "..." }],
         "user_keywords": {
            "worldview": ["关键词A"],
            "characters": ["关键词B"],
            "outline": ["关键词C"]
         }
      },
      "drafts": {
         "planning_draft_path": "scripts/<script_name>/drafts/planning_draft.md",
         "novel_draft_path": "scripts/<script_name>/drafts/novel_draft.md"
      },
      "style_contract": {
         "background_style_anchor": "anime visual novel background, clean lineart, soft global illumination, cinematic composition",
         "background_negative_anchor": "低质量, 模糊, 水印, 文本, 人物, 人影",
         "character_style_anchor": "anime visual novel character illustration, clean lineart, cel shading, stable character design",
         "character_negative_anchor": "低质量, 模糊, 水印, 文本, 畸形, 多余肢体"
      },
      "character_refs": [
         { "name": "林澈", "image": "assets/char_ref_林澈_v1.png" }
      ],
      "asset_manifest": [
         {
            "segment_id": "s1",
            "background_image": "assets/scene_s1.png",
            "character_image": "assets/char_林澈_calm.png"
         }
      ],
      "pipeline_state": {
         "stage": "4",
         "updated_at": "2026-02-28"
      }
   }
}
```

兼容规则：若历史脚本仅有顶层 `planning`，先读取并迁移到 `shared.planning`，再继续后续阶段。

## 执行步骤

1. 读取输入与目标：
   - 项目名 / 剧本名 / 风格 / 篇幅 / 目标受众
   - 偏好类型：视觉小说（线性叙事）
   - 大纲来源模式：`ai_auto` 或 `user_keywords`
   - 参考文章：默认《铁道银河之夜》（仅作风格参考，不复刻原文）
   - 审稿偏好：阶段2完成后是否需要用户先检查剧本（`review_after_stage2=true|false`）
   - 若为 `user_keywords`，收集关键词包（世界观 / 人设 / 大纲）

2. 阶段化执行（默认自动连续执行，不逐步询问）：
   - 阶段1（需求澄清与方案）：通过对话补齐缺失信息，先确认大纲来源模式（AI 自动或用户关键词），调用 `create-script` 并由其调用 `mcp_playwright-im_generate_text` 生成“规划草稿（传统文本）”，先落盘 `scripts/<script_name>/drafts/planning_draft.md`，再转换并写入 `shared.planning`（明确传入“原创创作，不参考其他剧本正文”约束）
   - 阶段2（文本剧本）：读取并注入 `scripts/<script_name>/drafts/planning_draft.md` 全文作为生文输入上下文，调用 `create-script` 并由其调用 `mcp_playwright-im_generate_text` 生成“正文草稿（传统小说文本）”；正文必须包含人物/环境/心理描写并混合对话，禁止纯对白。随后先落盘 `scripts/<script_name>/drafts/novel_draft.md`，再由 agent 转换为基础剧本文本；再调用 `configure-script-presentation` 添加 `effect`/`speed`/`display_break_lines`，并更新 `shared.pipeline_state`（其中 `typewriter` 速度固定为 `55`；文本阶段保持原创约束）
      - 阶段2超长稿策略：默认采用“分批续写 + 同一 `session_id`”模式；若上下文接近上限，启用 `context_files`（`planning_draft` 与已生成片段）并附加 `FileIDs` 继续续写，后续批次保持 `carry_forward_file_ids=true`。
      - 分批续写提示词默认要求“自然承接前文”，不强制每批结尾制造悬念；只有用户明确指定章节钩子时，才在对应批次增加悬念约束。
   - 阶段2结束后必须执行一致性校验：`title` 应与剧本文件名（不含 `.json`）一致；不一致则自动修正为文件名
   - 阶段2结束后审稿分支：
      - 若 `review_after_stage2=true`：暂停自动链路，提示用户检查 `novel_draft` 与 `script.json` 是否符合要求；用户可选择“按反馈重生成阶段2”或“确认通过继续阶段3/4”。
      - 若 `review_after_stage2=false`：不询问，自动继续阶段3与阶段4。
   - 阶段3（人物设定图）：调用 `generate-character-images` 按 `shared.planning.characters` 产出设定图并写入 `shared.character_refs`
   - 阶段4（场景资产与回写）：调用 `generate-scene-assets` 基于 `shared` 生成 `shared.asset_manifest`，再调用 `attach-script-assets` 回写到剧本
   - 仅当任一阶段失败或关键参数缺失时，再询问用户意见；其余场景默认自动继续执行

3. 阶段4降调用策略（必须执行）：
   - 先按“地点+时间+氛围”聚合段落，同类段落复用同一背景图
   - 同角色同情绪段落复用同一立绘，仅在情绪变化时新增
   - 默认每个主场景 1 张背景、每个角色 1-3 张情绪立绘
   - 若已有可复用资源路径，优先复用并跳过生图

4. 质量策略（必须执行）：
   - 阶段3人物设定图按“主视图+侧视图+后视图+装饰细节”生成。
   - 阶段4应用到剧本时，`character_image` 必须使用剧情立绘（`char_<name>_<mood>.png`），禁止直接回写 `char_ref_*`。
   - 背景图统一画风且禁止出现人物形象；同剧本所有背景共享统一风格锚点。
   - 提示词允许长文本，优先完整约束以提升质量。
   - 同一剧本的 `style_contract` 必须跨阶段复用，避免每张图风格漂移。
   - 生图服务调用默认开启：`enforce_style=true`、`strict_no_people=true`（背景）、`retry_max>=2`。

## 每阶段标准输入/输出模板

为保证链路稳定，按以下字段组织阶段数据（缺省字段可省略）：

### 阶段1（需求澄清与方案）

```json
{
   "stage": "1",
   "skill": "create-script",
   "input": {
      "script_name": "迷失之森",
      "mode": "planning",
      "style": "悬疑",
      "length": "short",
      "script_form": "visual_novel",
      "reference_article": {
         "title": "铁道银河之夜",
         "usage": "theme_tone_only"
      },
      "review_after_stage2": true,
      "planning_source": "user_keywords",
      "user_keywords": {
         "worldview": ["迷雾森林", "古代遗迹"],
         "characters": ["谨慎侦察员", "失踪向导"],
         "outline": ["进入禁区", "线索反转", "出口抉择"]
      }
   },
   "output": {
      "requirements_summary": "...",
      "worldview": "...",
      "characters": [{ "name": "林澈", "profile": "..." }],
      "outline": [{ "chapter": 1, "summary": "..." }],
      "script_form": "visual_novel",
      "planning_source": "user_keywords",
      "shared_written": ["planning", "pipeline_state"]
   }
}
```

### 阶段2（文本+演出效果剧本）

```json
{
   "stage": "2",
   "skill": "create-script + configure-script-presentation",
   "input": {
      "script_name": "迷失之森",
      "planning_draft_path": "scripts/迷失之森/drafts/planning_draft.md",
      "review_after_stage2": true,
      "planning": {
         "worldview": "...",
         "characters": [{ "name": "林澈" }],
         "outline": [{ "chapter": 1, "summary": "..." }],
         "script_form": "visual_novel"
      }
   },
   "output": {
      "novel_draft_path": "scripts/迷失之森/drafts/novel_draft.md",
      "script_path": "scripts/迷失之森/script.json",
      "review_gate": "pending_user_review|auto_continue|approved|regenerate_stage2",
      "includes_text": true,
      "includes_presentation": true,
      "includes_asset_fields": false,
      "shared_read": ["planning"],
      "shared_written": ["pipeline_state"]
   }
}
```

审稿分支状态示例：

- `review_after_stage2=true` 且待用户检查：`review_gate=pending_user_review`
- 用户确认通过并继续阶段3/4：`review_gate=approved`
- 用户要求按反馈重生文：`review_gate=regenerate_stage2`
- `review_after_stage2=false` 自动继续：`review_gate=auto_continue`

### 阶段3（人物设定图）

```json
{
   "stage": "3",
   "skill": "generate-character-images",
   "input": {
      "script_name": "迷失之森",
      "characters": [{ "name": "林澈", "profile": "..." }],
      "count_per_character": 1
   },
   "output": {
      "character_refs": [
         { "name": "林澈", "image": "assets/char_ref_林澈_v1.png" }
      ],
      "shared_read": ["planning", "style_contract"],
      "shared_written": ["character_refs", "pipeline_state"]
   }
}
```

### 阶段4（背景/立绘 + 应用到剧本）

```json
{
   "stage": "4",
   "skill": "generate-scene-assets + attach-script-assets",
   "input": {
      "script_path": "scripts/迷失之森/script.json",
      "script_name": "迷失之森",
      "character_refs": [
         { "name": "林澈", "image": "assets/char_ref_林澈_v1.png" }
      ]
   },
   "output": {
      "asset_manifest": [
         {
            "segment_id": "s1",
            "background_image": "assets/scene_s1.png",
            "character_image": "assets/char_林澈_calm.png"
         }
      ],
      "final_script_path": "scripts/迷失之森/script.json",
      "generated_background_count": 4,
      "generated_character_pose_count": 6,
      "reused_asset_count": 10,
      "updated_segments": 8,
      "shared_read": ["planning", "style_contract", "character_refs"],
      "shared_written": ["asset_manifest", "pipeline_state"]
   }
}
```

4. 结果汇总：
   - 需求摘要（风格、篇幅、剧本形态）
   - 大纲来源（`ai_auto` / `user_keywords`）与关键词使用说明
   - 草稿落盘路径（规划草稿、正文草稿）
   - 参考文章使用声明（默认《铁道银河之夜》，`theme_tone_only`）
   - 审稿分支配置与状态（`review_after_stage2`、最终 `review_gate`）
   - 文本剧本路径（含演出效果）
   - 人物设定图路径列表
   - 资产生成/复用统计与最终剧本路径
   - 原创性检查结果（阶段1/2未参考项目内其他剧本正文）

## 模型编排约束

- 文生图阶段：优先混元极速版（`TextToImageLite`）
- 图生图阶段：优先混元3.0任务接口（`SubmitTextToImageJob` + `QueryTextToImageJob`）

## 服务参数约定（质量稳定）

调用生图服务时，建议统一传入：

```json
{
   "scene_type": "background|character",
   "enforce_style": true,
   "style_anchor": "<来自 shared.style_contract.<scene_type>_style_anchor>",
   "negative_anchor": "<来自 shared.style_contract.<scene_type>_negative_anchor>",
   "strict_no_people": true,
   "retry_max": 3
}
```

提示词写作要求（必须执行）：
- 允许并鼓励长提示词；不少于“主体要素 + 构图镜头 + 光照色调 + 材质细节 + 用途约束”5段信息。
- 背景图需明确“文本可读区留白（如画面中央偏下避免高频细节）”。
- 角色立绘需明确“构图（半身/胸像）+ 表情强度 + 服装延续点 + 边缘清晰度要求”。

## 注意事项

- 编排 skill 只负责流程协调与阶段衔接；允许校验 `shared` 字段完整性，但不直接改写 `segments` 业务内容。
- 阶段1必须先对话澄清，不得在关键信息缺失时直接进入生图。
- 用户选择 `user_keywords` 时，阶段1必须先收齐关键词再进入文本创作；关键词不足则先补问。
- 阶段1需提前确认 `review_after_stage2` 偏好；未明确时默认 `false`（自动继续）。
- 阶段1/2 的生文结果必须先保存到 `scripts/<script_name>/drafts/` 后再做 JSON 转换。
- 阶段2生文请求必须包含 `planning_draft` 内容（优先全文），否则视为流程不合规。
- 阶段2若检测到正文草稿为纯对话体，应判定不合规并重试生文，而非直接进入转换。
- 阶段2产物不得包含 `background.image` / `character_image`。
- 任一阶段失败时，停止后续阶段并输出最小可恢复建议，再询问用户是否重试/跳过/终止。
- 阶段4默认优先复用，目标是减少不必要 API 调用。
- 若图生图接口仅接受 URL 参考图，应先确保参考图可被接口访问后再执行立绘生成。
- 任一子 skill 执行前，必须先读取脚本 `shared`；执行后必须写回本阶段新增字段并保留已有字段。
