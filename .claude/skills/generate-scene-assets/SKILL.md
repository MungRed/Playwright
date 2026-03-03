---
name: generate-scene-assets
description: 根据剧本与人物设定图生成流程中的背景图与人物立绘，并按是否图生图自动选择混元模型。关键词：背景图, 立绘, 图生图, 混元3.0, 极速版
---

## 功能说明

基于剧本段落与角色设定图批量生成：
- 场景背景图（`scripts/<script_name>/assets/`）
- 剧情流程中的人物立绘（可多角色/多情绪）

质量约束（必须执行）：
- 应用到剧本的 `character_image` 必须是“剧情立绘”产物，不可直接使用 `char_ref_*` 设定图。
- 背景图禁止出现人物形象（含远景人影）。
- 同一剧本背景图需保持统一画风（镜头语言、色彩体系、渲染质感一致）。
- 提示词允许长文本，需充分描述场景要素与风格约束，不做不必要压缩。

本 skill 仅负责“资产生成 + 资产清单输出”，不回写剧本 JSON。

## 共享数据读写（必须执行）

- 执行前必须读取脚本 `shared`：`planning`、`style_contract`、`character_refs`。
- `style_contract` 使用双锚点：
   - 背景：`background_style_anchor` / `background_negative_anchor`
   - 角色：`character_style_anchor` / `character_negative_anchor`
- 若 `character_refs` 缺失，允许回退外部输入，但执行后必须写回 `shared.character_refs`。
- 生成完成后必须写回 `shared.asset_manifest`（段落到资源映射）与 `shared.pipeline_state`（阶段4-asset 完成）。
- 不改写 `segments`；仅维护共享资产元数据。

并根据任务类型自动选模型：
- **无图生图**（纯文生图）：使用混元极速版
- **需要图生图**（参考人设图做一致性生成）：使用混元 3.0
  - 参考：`https://cloud.tencent.com/document/product/1668/124632`

## 执行步骤

1. 收集输入：
   - 剧本文件路径
   - 阶段1规划包（优先读取 `shared.planning`）
   - 角色设定图路径（优先读取 `shared.character_refs`）
   - 目标清单：要生成哪些场景与立绘

2. 场景拆分：
   - 先完整阅读剧本，再确定最小必要资产集
   - 从剧本中抽取关键场景（地点、时间、氛围）
   - 从角色信息抽取立绘要素（服装、情绪、姿态）

3. 降调用策略（必须执行）：
   - 按“地点+时间+氛围”聚合段落，默认同组复用同一背景图
   - 按“角色+情绪”聚合段落，默认同组复用同一立绘
   - 优先复用已存在资源（路径存在则不重复生图）
   - 仅在剧情出现新场景或情绪跃迁时新增生成任务

4. 模型选择：
   - 若无参考图 -> 混元极速版（文生图）
   - 若有参考图且要求风格/角色一致 -> 混元 3.0（图生图）

4.0 图生图前置检查：
   - 确保 `reference_images` 可通过 `https` 访问（详见 PITFALLS.md § 2.4）

4.1 立绘生成约束：
   - 强制使用图生图（混元 3.0），禁止退回文生图（详见 PITFALLS.md § 5.3）
   - 命名：`char_<name>_<mood>.png`，不得将 `char_ref_*` 直接当立绘回写
   - 分辨率必须为竖向 `720x1280`（详见 PITFALLS.md § 5.4）
   - 提示词分层描述：角色特征 + 情绪 + 构图 + 服装 + 质量约束

4.2 背景生成约束：
   - 提示词显式包含”无人场景”（详见 PITFALLS.md § 5.1）
   - 维护统一 `style_anchor`，确保同剧本画风一致（详见 PITFALLS.md § 5.2）
   - 调用时固定 `scene_type=background`、`enforce_style=true`、`strict_no_people=true`

5. 生成并落盘：
   - 背景推荐尺寸：`1280x720`
   - 立绘推荐尺寸：`720x1280`
   - 文件命名：`scene_<id>.png`、`char_<name>_<mood>.png`
   - 保存目录：`scripts/<script_name>/assets/`
   - 若使用 `TextToImageLite`，服务端会自动做分辨率归一化（横图→`1280x720`，竖图→`720x1280`，方图→`1024x1024`）以降低失败率。

6. 输出资产清单：
   - 给出段落到资产路径映射（用于后续 `attach-script-assets`）
   - 清单包含：`segment_id`、`background_image`、`character_image`
   - **`segment_id` 必须使用 `segments[i].id` 字段的实际值**（如 `"s1"`），不得使用数字字符串索引（`"0"`、`"1"`）
   - 路径必须使用生图工具实际返回的文件名（详见 PITFALLS.md § 1.2）
   - 将该清单写回 `shared.asset_manifest`
   - 统计包含：生成数、复用数、跳过数
   - 额外标注：`used_character_ref_to_generate_portrait: true/false`

## 注意事项

- 图生图场景优先混元 3.0，确保角色一致性
- 图生图失败时中断并询问用户，不得静默退回文生图
- 目标是在视觉可用前提下最小化 API 调用次数
- 最终以脚本内 `shared.asset_manifest` 为单一真值来源
- 详细约束参见 PITFALLS.md § 1, § 2, § 5

## 调用示例模板

### 模板 A：文生图（混元极速版 / TextToImageLite）

```json
{
   "script_name": "迷失之森",
   "prompt": "雨夜森林小路，电影感，薄雾，冷色调，无人物",
   "filename": "scene_forest_night.png",
   "negative_prompt": "低质量, 模糊, 水印, 文本",
   "width": 1280,
   "height": 720,
   "api_action": "TextToImageLite",
   "scene_type": "background",
   "style_anchor": "<shared.style_contract.background_style_anchor>",
   "negative_anchor": "<shared.style_contract.background_negative_anchor>",
   "enforce_style": true,
   "strict_no_people": true,
   "retry_max": 3
}
```

适用：仅需根据文本生成背景图或氛围图，不依赖参考图。

### 模板 B：图生图（混元 3.0 任务 / SubmitTextToImageJob）

```json
{
   "script_name": "午夜密室",
   "prompt": "同一角色站在地铁站台，半身构图，侦探风衣，夜景霓虹，情绪紧张",
   "filename": "char_detective_tense.png",
   "negative_prompt": "低质量, 模糊, 水印, 文本, 变形",
   "width": 720,
   "height": 1280,
   "api_action": "SubmitTextToImageJob",
   "scene_type": "character",
   "style_anchor": "<shared.style_contract.character_style_anchor>",
   "negative_anchor": "<shared.style_contract.character_negative_anchor>",
   "enforce_style": true,
   "retry_max": 3,
   "reference_images": [
      "assets/char_ref_侦探_v1.png"
   ]
}
```

适用：需要保持角色外观一致（有参考图）的人物立绘或连续镜头资产。

`reference_images` 支持：
- 本地路径（如 `scripts/<script_name>/assets/char_ref_*.png`）：当 `COS_AUTO_UPLOAD_ENABLED=true` 时，服务自动按内容哈希上传并复用 URL，无需手动处理。
- 公开 URL：直接传入，无需 COS 配置。
