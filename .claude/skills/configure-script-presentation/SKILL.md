---
name: configure-script-presentation
description: 根据剧本文本为段落配置表现字段（如渐入、震动、速度等），不负责文本创作和生图。关键词：演出, effect, speed, 背景效果, 剧本表现
---

## 功能说明

读取剧本 JSON 后，按文本语义为每段配置表现字段，产出“可直接播放”的演出层配置。

本 skill 可独立使用，不属于剧本资产生产主链路的必经步骤。

## 执行步骤

1. 读取脚本并识别段落情绪：
   - 平稳叙述、对话、惊吓、神秘、高潮等

2. 应用表现映射规则：
   - 平稳叙述 -> `effect: fadein`, `speed: 20-35`
   - 对话/独白 -> `effect: typewriter`, `speed: 50-80`
   - 惊吓/冲击 -> `effect: shake`, `speed: 15-20`
   - 奇幻/神秘 -> `effect: wave`, `speed: 18-25`

3. 背景效果建议（如用户允许）：
   - 场景切换明显处建议 `background.effects: ["fade"]`
   - 冲击段落建议 `background.effects: ["shake"]`

4. 写回与汇总：
   - 仅修改表现字段：`effect`、`speed`、`background.effects`、`fade_ms`、`shake_ms`、`shake_strength`
   - 输出受影响段落数量和关键调整点

## 默认值

- 未匹配到强情绪时：`effect: fadein`、`speed: 30`

## 注意事项

- 不改写 `text` 文本内容。
- 不新增图片文件；仅处理 JSON 表现层。
- 不负责 `background.image` 与 `character_image` 的回写。
- 保持精确改动，避免无关格式化。
