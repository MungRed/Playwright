---
name: attach-script-assets
description: 将已生成的背景图与人物立绘路径回写到剧本 JSON，用于最终资源绑定。关键词：回写, 资源绑定, background.image, character_image, 剧本
---

## 功能说明

将资产生成阶段产出的文件路径写回剧本段落：
- `background.image`
- `character_image`

本 skill 只处理“路径绑定”，不生成文本、不生成图片、不配置演出字段。

## 执行步骤

1. 读取输入：
   - 目标剧本路径
   - 资产清单（`segment_id` -> 背景图路径、人物图路径）
   - 回写策略：仅补缺或允许覆盖（默认仅补缺）

2. 识别剧本结构：
   - 线性：`segments: []`
   - 分支：`start + segments: {}`

3. 执行最小回写：
   - 有背景映射时写入 `background.image`
   - 有人物映射时写入 `character_image`
   - 保留段落已有 `effect`、`speed`、`text` 与分支结构

4. 一致性校验：
   - `segment_id` 对应段落必须存在
   - 路径建议使用 `docs/scenes/<script_name>/...`
   - 不创建无映射的空字段

5. 输出结果：
   - 成功回写段落数
   - 新增/跳过/覆盖统计
   - 最终剧本路径

## 默认值

- 回写策略默认“仅补缺，不覆盖已有路径”

## 输入清单模板

```json
[
   {
      "segment_id": "s1",
      "background_image": "docs/scenes/迷失之森/scene_s1.png",
      "character_image": "docs/scenes/迷失之森/char_林澈_calm.png"
   }
]
```

## 注意事项

- 不修改剧情文本与分支逻辑。
- 不负责图片生成；依赖 `generate-scene-assets` 的产物。
- 保持精确改动，避免无关格式化。
