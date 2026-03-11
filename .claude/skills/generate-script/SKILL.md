---
name: generate-script
description: 独立执行剧本模块：根据完整小说生成 script.json 分镜与脚本结构。关键词：script, storyboards, module2
---

## 职责

仅负责模块2：根据完整小说生成 `script.json`。

- 输入：`scripts/<script_name>/drafts/novel_full.md`
- 输出：`scripts/<script_name>/script.json`
- 数据回写：`storyboards`、`shared.pipeline_state`

不负责小说生成，不负责分镜与生图。

## 文档先行（必须）

执行前先确认剧本模块文档已包含：
- 输入
- 输出
- 验收标准

## 关键约束

1. 剧本文本必须通过混元生文 API 生成。
2. 必须注入完整小说正文作为上下文。
3. 若 `effect=typewriter`，`speed` 固定为 `55`。
4. 写回时必须保留 `shared` 非目标字段。
5. 禁止单次生成全量剧本；必须按分镜分批生成（至少 2 批）。
6. 任一批次超时时，需复用同一 `session_id` 续写，并降低该批目标规模后重试。
7. 分批粒度默认是"一个分镜一次调用"；每次请求仅生成一个 `storyboard` 对象。
8. 初稿生成后不得直接结束；必须进入“本地门禁 -> 模型复评 -> 定向改写”的质量闭环。
9. 本地门禁默认使用 `tools/check_script_quality.py --min-narration-ratio 0.45`。
10. 质量闭环最多执行 3 轮；未达到停止条件前不得进入模块3。

## 段落类型规范（必须）

每个 storyboard 的 `scripts` 数组必须包含两类段落：

**旁白段落**（`speaker: "旁白"`）
- 取自小说的环境描写、感官细节、氛围渲染、内心独白
- 必须保留小说原文的文学感，禁止大幅简化
- 不含 `character_image` 字段（或设为 `null`）
- 每条旁白 `text` 不超过 80 字，过长须拆分为多条

**对话段落**（`speaker: 人物名`）
- 直接对话内容，可附带简短动作描写（括号标注）
- 必须含 `character_image` 字段（路径待模块3填充，生成时可留 `null`）
- 说话人使用小说中的人物称谓（如"盲眼法医"、"白裙女孩"等）

**交替规则**：
- 同一 storyboard 内旁白与对话交替出现，旁白占比不低于 40%
- storyboard 必须以旁白开头（场景建立）
- 分镜切换处必须有旁白标注时间/场景变化

## 质量闭环（必须）

固定顺序：
1. 初稿生成后先执行本地质量门禁。
2. 若存在旁白不足、重复表达、超长文本或字段问题，先使用本地工具修复：
	- `tools/enrich_script_narration.py`
	- `tools/auto_refine_script.py`
3. 本地门禁通过后，再调用 `review-script` 进行混元复评。
4. 若复评指出问题，则按以下优先级定向改写：
	- 角色动机与人物区分度
	- 主角特殊能力与破案线索的绑定
	- 氛围、旁白与文学化表达
	- 关键转折的铺垫与回收
5. 改写后重新执行“本地门禁 + 模型复评”。

## 停止条件（必须）

满足以下任一条件才可判定模块2完成：

1. `review-script` 返回 `quality_gate=pass`，且本地门禁通过。
2. 本地门禁通过，且模型复评满足以下“可交付阈值”：
	- `overall_score >= 6.5`
	- `story_completeness >= 7`
	- `visual_novel_adaptation >= 7`
	- `character_development >= 6`
	- `literary_quality >= 6`
	- `creativity_theme >= 6`
	- 无精确重复段落

若达到第 2 条，即使模型仍返回 `rewrite_needed`，也应标记为“可交付但可继续润色”，允许进入模块3。

## 执行流程

1. 读取 `script.json` 与完整小说正文。
2. 先生成分镜大纲（`storyboards` 骨架：每个分镜的主题、冲突、场景背景）。
3. 按分镜逐次调用混元生文 API 生成 `scripts` 列表（一次只生成一个分镜）：
	- 固定同一 `session_id`
	- `use_session_history=true`
	- 单次仅返回一个 `storyboard` 对象，避免超时
4. 若某分镜批次超时，缩小为 1-3 条 script 重试，最多 3 次。
5. 合并为完整 `storyboards -> scripts` 结构并校验可达性与字段合法性。
6. 执行本地门禁；若失败则先用本地工具修复并重检。
7. 调用 `review-script` 做混元复评，并按弱项执行定向改写。
8. 重复第 6-7 步，直到满足停止条件或达到 3 轮上限。
9. 写回 `script.json`，同步更新 `shared.pipeline_state`（至少包含 `quality_round`、`quality_gate`、`quality_scores`）。
10. 输出结构自检结论与质量闭环结论（字段合法性、标题一致性、分镜可达性、分批统计、最终停止原因）。

## 输出

- `script.json` 路径
- 段落数量与结构校验摘要
- `shared.pipeline_state` 更新摘要
- 分批生成摘要（分镜批次数、超时重试次数）
- 质量闭环摘要（轮次数、最终评分、停止条件命中项）
- 失败时提供 `重试 / 降级 / 终止` 选项