---
name: orchestrate-script-production
description: 仅负责统筹并串联剧本相关子 skill 的端到端流程。关键词：编排, 流程, pipeline, orchestration, 剧本生产
---

## 功能说明

按固定流程调用子 skill，形成可落地的剧本生产流水线：
1) 与用户对话澄清需求，产出人设、剧本大纲与基础形态（少选项小说 / 多选项文字冒险）
2) 基于阶段1结果生成“仅文本+演出效果”的剧本（不含背景图与人物图路径）
3) 基于阶段1结果生成人物设定图
4) 重新阅读剧本后生成背景图与人物立绘，并回写到剧本

## 共享数据协议（必须遵守）

所有子 skill 必须共享同一份脚本内数据源：`scripts/<script_name>.json` 顶层 `shared`。

推荐结构：

```json
{
   "shared": {
      "planning": {
         "requirements_summary": "...",
         "script_form": "novel_light_choices",
         "worldview": "...",
         "characters": [{ "name": "林澈", "profile": "..." }],
         "outline": [{ "chapter": 1, "summary": "..." }]
      },
      "style_contract": {
         "background_style_anchor": "anime visual novel background, clean lineart, soft global illumination, cinematic composition",
         "background_negative_anchor": "低质量, 模糊, 水印, 文本, 人物, 人影",
         "character_style_anchor": "anime visual novel character illustration, clean lineart, cel shading, stable character design",
         "character_negative_anchor": "低质量, 模糊, 水印, 文本, 畸形, 多余肢体"
      },
      "character_refs": [
         { "name": "林澈", "image": "docs/scenes/迷失之森/char_ref_林澈_v1.png" }
      ],
      "asset_manifest": [
         {
            "segment_id": "s1",
            "background_image": "docs/scenes/迷失之森/scene_s1.png",
            "character_image": "docs/scenes/迷失之森/char_林澈_calm.png"
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
   - 偏好类型：少选项小说 or 多选项文字冒险

2. 阶段化执行（逐步确认）：
   - 阶段1（需求澄清与方案）：通过对话补齐缺失信息，调用 `create-script` 并写入 `shared.planning`
   - 阶段2（文本剧本）：调用 `create-script` 生成基础剧本，再调用 `configure-script-presentation` 添加 `effect`/`speed`，并更新 `shared.pipeline_state`
   - 阶段3（人物设定图）：调用 `generate-character-images` 按 `shared.planning.characters` 产出设定图并写入 `shared.character_refs`
   - 阶段4（场景资产与回写）：调用 `generate-scene-assets` 基于 `shared` 生成 `shared.asset_manifest`，再调用 `attach-script-assets` 回写到剧本

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
      "script_form": "novel_light_choices"
   },
   "output": {
      "requirements_summary": "...",
      "worldview": "...",
      "characters": [{ "name": "林澈", "profile": "..." }],
      "outline": [{ "chapter": 1, "summary": "..." }],
      "script_form": "novel_light_choices",
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
      "planning": {
         "worldview": "...",
         "characters": [{ "name": "林澈" }],
         "outline": [{ "chapter": 1, "summary": "..." }],
         "script_form": "novel_light_choices"
      }
   },
   "output": {
      "script_path": "scripts/迷失之森.json",
      "includes_text": true,
      "includes_presentation": true,
      "includes_asset_fields": false,
      "shared_read": ["planning"],
      "shared_written": ["pipeline_state"]
   }
}
```

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
         { "name": "林澈", "image": "docs/scenes/迷失之森/char_ref_林澈_v1.png" }
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
      "script_path": "scripts/迷失之森.json",
      "script_name": "迷失之森",
      "character_refs": [
         { "name": "林澈", "image": "docs/scenes/迷失之森/char_ref_林澈_v1.png" }
      ]
   },
   "output": {
      "asset_manifest": [
         {
            "segment_id": "s1",
            "background_image": "docs/scenes/迷失之森/scene_s1.png",
            "character_image": "docs/scenes/迷失之森/char_林澈_calm.png"
         }
      ],
      "final_script_path": "scripts/迷失之森.json",
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
   - 文本剧本路径（含演出效果）
   - 人物设定图路径列表
   - 资产生成/复用统计与最终剧本路径

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
- 阶段2产物不得包含 `background.image` / `character_image`。
- 任一阶段失败时，停止后续阶段并输出最小可恢复建议。
- 阶段4默认优先复用，目标是减少不必要 API 调用。
- 若图生图接口仅接受 URL 参考图，应先确保参考图可被接口访问后再执行立绘生成。
- 任一子 skill 执行前，必须先读取脚本 `shared`；执行后必须写回本阶段新增字段并保留已有字段。
