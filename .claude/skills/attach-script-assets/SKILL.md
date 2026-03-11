---
name: attach-script-assets
description: 将 shared.asset_manifest 中的背景图与立绘路径回写到剧本段落，用于阶段3最终资产绑定。关键词：回写, 资源绑定, asset_manifest
---

## 职责

仅做最终资产路径绑定：
- `background.image`
- `character_image`

说明：本 skill 是“模块3图片资产生成”完成后的可选绑定步骤，不是主流程三模块之一。

## 关键规则

1. 默认从 `shared.asset_manifest` 读取映射。
2. `segment_id` 必须匹配段落 `id`。
3. 写回前核验资源路径存在。
4. 只更新目标字段，保留段落与 `shared` 其他内容。

## 执行流程

1. 读取 `script.json` 与 `shared.asset_manifest`。
2. 按段落 `id` 执行最小回写（默认仅补缺）。
3. 更新 `shared.pipeline_state`（绑定完成、统计信息）。
4. 输出回写统计与未命中项。
