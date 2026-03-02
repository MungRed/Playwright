---
name: create-script
description: 生成世界观、人设与剧本文本，并可输出仅文本的基础剧本 JSON；不负责图片与资源回写。关键词：世界观, 人设, 剧本, 文本, 视觉小说, story, script
---

## 功能说明

用于生成或改写“纯文本层”内容：
- 需求澄清结果（用户偏好摘要）
- 世界观设定
- 角色设定（人设）
- 剧本大纲
- 剧本段落文本（视觉小说线性叙事）

本 skill **不负责**：`background.image`、`character_image` 回写、视觉演出参数与生图流程。

## 共享数据读写（必须执行）

- 统一从 `scripts/<script_name>.json` 顶层 `shared` 读取上下文。
- 阶段1产物必须写入 `shared.planning`。
- 若历史脚本存在顶层 `planning` 但无 `shared.planning`，需先兼容读取，并在写回时迁移到 `shared.planning`。
- 写回时保留 `shared` 其他字段（如 `style_contract`、`character_refs`、`asset_manifest`）。

## 执行步骤

1. 确认任务范围：
	- 新建文本内容（世界观/人设/剧本）或修改现有文本内容
	- 若涉及 JSON 文件，先读取并定位目标段落 ID / 数组索引

2. 按缺失信息提问（仅缺失时提问）：
	- 用户希望的剧本形态：视觉小说（线性叙事）
	- 输出范围：仅世界观、仅人设、仅剧本，或三者组合
	- 是否先产出“规划包”（人设+大纲+形态）
	- 是否要求“基础剧本模式”（仅文本字段，不含任何资源路径）
	- 剧本结构：线性（`segments: []`）
	- `title`、`description`、目标篇幅与风格

3. 生成脚本结构（严格 JSON）：
	- 视觉小说标准结构：`title`、`description`、`segments`（数组）
	- 顶层确保存在 `shared`，并写入/更新 `shared.planning`
	- 段落字段仅生成文本相关：`text`、`next`、`speaker`（可选）
	- 同段分步显示仅使用 `display_break_lines`（可选，按原文行号断点）
	- 可生成 `speaker` 作为文本标注，但不生成图片路径字段

4. 自检并修复：
	- 所有 `next`（若存在）必须指向存在段落 ID
	- 不生成交互跳转字段（如 `choices`）
	- 若生成 `display_break_lines`，断点值必须为递增整数且落在 `1 <= n < 行数`
	- `shared.planning` 字段完整（`requirements_summary`、`worldview`、`characters`、`outline`、`script_form`）
	- 不输出注释，不输出图片/演出字段

5. 写入文件并输出摘要：
	- 文件路径、脚本类型、段落数、是否为基础剧本
	- 世界观/人设/大纲/剧本是否已覆盖
	- `shared` 读写情况（读取了哪些字段、写入了哪些字段）

## 规划包输出模板（用于编排阶段1）

```json
{
	"shared": {
		"planning": {
	"requirements_summary": "...",
	"script_form": "visual_novel",
	"worldview": "...",
	"characters": [
		{ "name": "林澈", "profile": "..." }
	],
	"outline": [
		{ "chapter": 1, "summary": "..." }
	]
		}
	}
}
```

## 默认值（用户未指定时）

- 新建脚本默认采用视觉小说线性结构
- 剧本文本默认第三人称叙述 + 关键段落可带对话
- 未指定剧本形态时，默认视觉小说（`visual_novel`）

## 示例（纯文本线性脚本）

```json
{
  "title": "迷雾车站",
  "description": "一个发生在深夜车站的短篇故事",
  "segments": [
		{
			"text": "午夜时分，你独自站在空荡站台。",
			"next": "1"
		},
		{
			"text": "远处传来列车鸣笛，雾气逐渐逼近。",
		"speaker": "旅人"
		}
  ]
}
```