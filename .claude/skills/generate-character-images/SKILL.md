---
name: generate-character-images
description: 根据剧本人设生成角色设定图（阶段3-人设子阶段），支持独立执行并写回 shared.character_refs。关键词：人物, 人设, 生图, character refs
---

## 职责

根据 `shared.planning.characters` 生成人设图，并写回 `shared.character_refs`。

说明：本 skill 是“模块3图片资产生成”的可选辅助能力，不是主流程三模块之一。

## 文档先行（必须）

- 执行前确认资产阶段文档已说明：角色清单、风格锚点、输出验收标准。

## 关键约束

1. 优先读取 `shared.planning.characters`，缺失时再向用户补齐最小人设信息。
2. 必须使用 `assets/_style_contract.json` 中的角色风格锚点。
3. 设定图必须为“三视图”（正面/侧面/背面）角色设定单。
4. 输出写入 `scripts/<script_name>/assets/char_ref_<name>_v1.png`。
5. 三视图设定图用于后续图生图参考，不可直接作为阅读器 `character_image`。
6. 写回时只更新 `shared.character_refs` 与 `shared.pipeline_state`。

## 执行流程

1. 读取 `shared`：`planning`、`style_contract`、`character_refs`。
2. 为每个角色构造三视图提示词（角色特征 + 服装 + 正侧背构图 + 风格锚点）。
3. 调用生图工具批量生成或复用已存在设定图。
4. 写回 `shared.character_refs` 与阶段统计。

## 输出

- 新增与复用数量
- 每个角色对应的设定图路径
- 失败项与建议重试策略
