---
name: generate-scene-assets
description: 根据剧本生成模块3图片资产（人设图/背景图/立绘）并回写 shared.asset_manifest。关键词：图片资产, 背景图, 立绘, character refs, asset manifest
---

## 职责

作为模块3，独立生成并绑定图片资产：
- 人设图（可复用或增量生成）
- 分镜对应背景图（无人物）
- 角色立绘（按情绪/场景），并回写到各段落 `character_image`
- 资产清单（`shared.asset_manifest`）

## 文档先行（必须）

- 执行前确认资产阶段文档包含：场景列表、角色情绪列表、复用策略、验收标准。

## 关键约束

1. 背景图必须显式“无人物”。
2. 角色一致性必须优先复用 `shared.character_refs`；缺失时先文生图生成“人物三视图设定图”（正/侧/背）。
3. 统一使用 `assets/_style_contract.json` 中的风格锚点，避免风格漂移。
4. 写回目标：`scripts[].character_image`、`shared.asset_manifest`、`shared.character_refs`、`shared.pipeline_state`。
5. `segment_id` 必须使用段落真实 `id`，不能用数组索引。
6. 禁止在模块3再次生成或改写分镜 JSON；分镜结构以 `script.json` 中 `storyboards` 为唯一输入。
7. 剧情立绘必须走图生图（`SubmitTextToImageJob` + `reference_images=char_ref`），输出竖版图（推荐 `720x1280`）。
8. 回写到 `character_image` 的必须是竖版立绘路径，不可回写三视图设定图。

## 执行流程

### 1. 读取剧本数据
读取 `script.json` 与 `shared`（`planning/style_contract/character_refs`）。

### 2. 提取图片需求
基于 `storyboards -> scripts` 提取最小图片需求（背景、人物、情绪）。

### 3. 生成角色三视图（人设图）

**前置条件检查**:
- 对于每个角色，检查 `shared.character_refs[角色名].three_view_ref` 是否存在
- 若不存在，调用 `engine/character_design_generator.py::generate_three_view_design()`

**三视图生成参数**:
- **角色描述**: 从 `shared.planning.characters` 或剧本中提取
- **风格锚点**: 从 `shared.style_contract.global_style_anchor` 获取
- **输出路径**: `assets/char_ref_{角色名}_front.png`（+left/right）
- **API**: `TextToImageLite`（文生图）
- **分辨率**: `1280x720`（横版，用于设定图）
- **提示词模板**: `{角色描述}, {视角}, 角色设定单, 三视图, {风格锚点}, clean lineart, character turnaround sheet, white background`
- **负向提示词**: `背景, 多角色, 文字, 水印, 低质量, 模糊`

**写回**:
```python
shared["character_refs"][角色名] = {
    "three_view_ref": "assets/char_ref_{角色名}_front.png",
    "description": 角色描述,
    "style_anchor": 角色风格锚点,
}
```

### 4. 生成背景图

**背景图生成参数**:
- **API**: `TextToImageLite`（文生图）
- **分辨率**: `1280x720`（横版）
- **提示词**: 基于分镜 `title` 和 `background` 描述
- **负向提示词**: `人物, 人影, 路人, 角色, 文字, 水印`（强制无人物）
- **strict_no_people**: `true`

### 5. 生成角色剧情立绘（图生图）

**立绘生成流程（强制）**:

**前置条件**:
- 确认 `assets/char_ref_{角色名}_front.png`（或three_view_ref）存在
- 若不存在，先执行步骤3

**立绘生成参数**:
- **API**: `SubmitTextToImageJob`（图生图，**禁止使用 TextToImageLite**）
- **reference_images**: `[scripts/{script_name}/assets/char_ref_{角色名}_front.png]`
- **分辨率**: `720x1280`（**竖版**，用于游戏显示）
- **提示词模板**: `{角色名}, {表情状态}, 半身构图, 竖版立绘, {风格锚点}`
- **负向提示词**: `背景, 环境, 多角色, 全身, 横版, 低质量, 模糊`
- **revise_prompt**: `true`（开启AI优化）
- **logo_add**: `0`（不添加水印）

**生成状态清单**（至少生成default）:
- `default`（默认/平静）
- `angry`（愤怒）
- `sad`（悲伤）
- `happy`（高兴）
- `surprised`（惊讶）

**立绘命名规范**:
- `char_{角色名}_{状态}.png`
- 示例：`char_沈砚_default.png`, `char_顾行舟_angry.png`

**资产绑定规范**:
- `character_image` 必须绑定**竖版立绘**，禁止直接使用三视图
- 示例：`"character_image": "assets/char_沈砚_default.png"`

### 6. 构建资产清单

形成 `asset_manifest`：
```json
[
  {
    "segment_id": "s1",
    "background_image": "assets/scene_1_rain_night_dock.png",
    "character_image": null
  },
  {
    "segment_id": "s2",
    "background_image": "assets/scene_1_rain_night_dock.png",
    "character_image": "assets/char_沈砚_default.png"
  }
]
```

### 7. 写回剧本数据

**写回目标**:
- `scripts[].character_image`：回写竖版立绘路径
- `shared.asset_manifest`：完整资产清单
- `shared.character_refs`：角色三视图与立绘路径
- `shared.pipeline_state.stage`：更新为 `module3_completed`
- `shared.pipeline_state.asset_stats`：生成/复用/失败统计

## 输出

- 图片资产目录与摘要
- 资产清单路径与摘要
- 人设图与立绘对应关系摘要（`char_ref -> character_image`）
- 生成/复用/失败统计
- `shared.asset_manifest` 完整条目数
