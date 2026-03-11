---
name: review-script
description: 调用腾讯混元对剧本进行评分与分析，作为阶段2质量门禁与改写依据。关键词：评分, 评测, 审阅, review, quality gate
---

## 职责

对剧本做多维评分并给出可执行改写建议，作为阶段2是否进入阶段3的门禁。

## 文档先行

- 执行前确认剧本阶段文档已定义验收阈值与评审口径。

## 执行流程

1. 读取目标 `script.json`（含 `shared.planning` 与 `storyboards`）。
2. 将剧本内容整理为结构化文本并通过 `.txt` 上下文传给混元生文 API。
3. 输出标准化评分结果并写入 `scripts/<script_name>/review.json`。
4. 基于评分结果补充“是否可交付”的统一判断，避免不同 agent 口径漂移。

## 最低输出字段

- `ratings`（分维度）
- `overall_score`
- `strengths`
- `weaknesses`
- `suggestions`
- `quality_gate`
- `delivery_gate`（推荐新增，取值：`pass` / `pass_with_polish` / `rewrite_needed`）
- `stop_reason`（推荐新增，说明为何停止或继续迭代）

## 关键约束

1. 不修改原剧本正文，仅生成评审报告。
2. `context_files` 仅使用 `.txt`。
3. 严格评审默认开启，建议可定位到具体段落。
4. 评审口径统一为 0-10 分制，不再使用旧的 0-100 / 70 分门槛。

## 统一判定口径（必须）

1. 若模型返回 `quality_gate=pass`，则 `delivery_gate=pass`。
2. 若模型返回 `rewrite_needed`，但同时满足以下条件，则 `delivery_gate=pass_with_polish`：
	- `overall_score >= 6.5`
	- `story_completeness >= 7`
	- `visual_novel_adaptation >= 7`
	- 其余核心维度均 >= 6
	- 调用方确认本地门禁已通过
3. 其他情况一律为 `delivery_gate=rewrite_needed`。

## 输出解释（必须）

- `quality_gate` 保留模型原始结论。
- `delivery_gate` 是供编排 skill 使用的统一停止条件。
- 当 `delivery_gate=pass_with_polish` 时，表示可进入模块3，但仍应保留后续润色建议。
