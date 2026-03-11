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

1. 读取 `script.json` 与 `shared`（`planning/style_contract/character_refs`）。
2. 基于 `storyboards -> scripts` 提取最小图片需求（背景、人物、情绪）。
3. 检查 `shared.character_refs`：缺失角色先文生图生成三视图人设图并写回。
4. 先生成背景图（无人物），再以人设图为参考执行图生图生成竖版剧情立绘。
5. 立绘命名建议：`char_<name>_<mood>.png`，并用于段落 `character_image` 回写。
6. 形成 `asset_manifest`：`segment_id/background_image/character_image`。
7. 写回 `shared.asset_manifest` 与 `shared.pipeline_state`。

## 输出

- 图片资产目录与摘要
- 资产清单路径与摘要
- 人设图与立绘对应关系摘要（`char_ref -> character_image`）
- 生成/复用/失败统计
- `shared.asset_manifest` 完整条目数
