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

## 执行步骤

1. 读取输入与目标：
   - 项目名 / 剧本名 / 风格 / 篇幅 / 目标受众
   - 偏好类型：少选项小说 or 多选项文字冒险

2. 阶段化执行（逐步确认）：
   - 阶段1（需求澄清与方案）：通过对话补齐缺失信息，调用 `create-script` 输出人设、大纲与剧本形态
   - 阶段2（文本剧本）：调用 `create-script` 生成基础剧本，再调用 `configure-script-presentation` 添加 `effect`/`speed`
   - 阶段3（人物设定图）：调用 `generate-character-images` 按阶段1人设产出角色设定图
   - 阶段4（场景资产与回写）：调用 `generate-scene-assets` 生成背景/立绘，再调用 `attach-script-assets` 回写到剧本

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
      "script_form": "novel_light_choices"
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
      "includes_asset_fields": false
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
      ]
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
      "updated_segments": 8
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

## 注意事项

- 编排 skill 只负责流程协调与阶段衔接，不直接改写业务数据。
- 阶段1必须先对话澄清，不得在关键信息缺失时直接进入生图。
- 阶段2产物不得包含 `background.image` / `character_image`。
- 任一阶段失败时，停止后续阶段并输出最小可恢复建议。
- 阶段4默认优先复用，目标是减少不必要 API 调用。
- 若图生图接口仅接受 URL 参考图，应先确保参考图可被接口访问后再执行立绘生成。
