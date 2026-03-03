---
name: configure-script-presentation
description: 根据剧本文本为段落配置表现字段（如打字机、震动、速度等），不负责文本创作和生图。关键词：演出, effect, speed, 背景效果, 剧本表现
---

## 功能说明

读取剧本 JSON 后，按文本语义为每段配置表现字段，产出“可直接播放”的演出层配置。

本 skill 可独立使用，不属于剧本资产生产主链路的必经步骤。

## 共享数据读写（必须执行）

- 执行前读取 `shared`（至少读取 `shared.planning`）。
- 可选读取 `shared.style_contract` 以统一演出节奏（例如同类场景速度区间）。
- 执行后更新 `shared.pipeline_state`（标记阶段2完成、时间戳、影响段落数）。
- 严禁清空或覆盖 `shared` 其他字段。

## 执行步骤

1. 读取脚本并识别段落情绪：
   - 平稳叙述、对话、惊吓、神秘、高潮等

2. 应用表现映射规则：
   - 平稳叙述 -> `effect: typewriter`, `speed: 55`
   - 对话/独白 -> `effect: typewriter`, `speed: 55`
   - 惊吓/冲击 -> `effect: shake`, `speed: 15-20`
   - 奇幻/神秘 -> `effect: typewriter`, `speed: 55`

3. 背景效果建议（如用户允许）：
   - 场景切换明显处建议 `background.effects: ["fade"]`
   - 冲击段落建议 `background.effects: ["shake"]`

4. 写回与汇总：
   - 仅修改表现字段：`effect`、`speed`、`display_break_lines`、`background.effects`、`fade_ms`、`shake_ms`、`shake_strength`
   - `display_break_lines` 使用**字符串数组**格式：每项为该步骤新增的一行文本（非累积），引擎按步累积拼接渲染；有此字段时 `text` 必须留空 `""`
   - 禁止在 `text` 中写入 `\n`；分行完全由 `display_break_lines` 控制
   - 追加更新 `shared.pipeline_state`
   - 输出受影响段落数量和关键调整点

## 默认值

- 未匹配到强情绪时：`effect: typewriter`、`speed: 55`
- `typewriter` 速度固定为 `55`，不因情绪类型调整。

## 注意事项

- 不改写 `text` 文本内容。
- 不新增图片文件；仅处理 JSON 表现层。
- 不负责 `background.image` 与 `character_image` 的回写。
- 保持精确改动，避免无关格式化。
- 不改写 `shared.planning`、`shared.character_refs`、`shared.asset_manifest`。
