---
name: configure-script-presentation
description: 为剧本段落配置演出字段（effect/speed/background effects），作为阶段2可选后处理。关键词：演出, effect, speed, 剧本表现
---

## 职责

只处理剧本表现层，不负责文本创作与资产生成。

## 文档先行

- 执行前确认剧本阶段文档已定义演出规则（何处分步、何处震动、何处渐变）。

## 规则

1. 默认 `effect=typewriter` 且 `speed=55`。
2. 禁止在 `text` 中写 `\n` 作为分步手段。
3. 仅更新表现字段与 `shared.pipeline_state`。

## 输出

- 受影响段落数量
- 关键演出变更摘要
- 与阶段文档一致性结论
