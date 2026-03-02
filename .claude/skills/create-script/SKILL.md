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

## 原创约束（必须执行）

- 创作世界观/人设/剧情文本时，禁止参考项目中已有剧本正文（`scripts/*.json`）作为素材来源。
- 仅允许读取“当前目标脚本文件”用于续写、改写或结构修复；禁止从其他剧本抽取设定、情节、对白、命名。
- 用户若明确要求“仿照某现有剧本”，应拒绝照搬并改为提供同题材但全新设定与情节。
- 输出文本必须保证原创，不得出现对仓库现有剧本可识别的段落复用或近似改写。

## 共享数据读写（必须执行）

- 统一从 `scripts/<script_name>.json` 顶层 `shared` 读取上下文。
- 阶段1产物必须写入 `shared.planning`。
- 若历史脚本存在顶层 `planning` 但无 `shared.planning`，需先兼容读取，并在写回时迁移到 `shared.planning`。
- 写回时保留 `shared` 其他字段（如 `style_contract`、`character_refs`、`asset_manifest`）。

## 执行步骤

1. 确认任务范围：
	- 新建文本内容（世界观/人设/剧本）或修改现有文本内容
	- 若涉及 JSON 文件，先读取并定位目标段落 ID / 数组索引
	- 若为新建创作，禁止读取其他 `scripts/*.json` 作为创意参考

2. 按缺失信息提问（仅缺失时提问）：
	- 用户希望的剧本形态：视觉小说（线性叙事）
	- 大纲来源：`AI 自动生成` 或 `用户提供关键词`
	- 若选择“用户提供关键词”，补齐：世界观关键词、人物设定关键词、剧情大纲关键词（可分别提供）
	- 输出范围：仅世界观、仅人设、仅剧本，或三者组合
	- 是否先产出“规划包”（人设+大纲+形态）
	- 是否要求“基础剧本模式”（仅文本字段，不含任何资源路径）
	- 剧本结构：线性（`segments: []`）
	- `title`、`description`、目标篇幅与风格

3. 生成脚本结构（严格 JSON）：
	- 视觉小说标准结构：`title`、`description`、`segments`（数组）
	- 顶层确保存在 `shared`，并写入/更新 `shared.planning`
	- `shared.planning` 必须写入 `planning_source`：`ai_auto` 或 `user_keywords`
	- 若 `planning_source=user_keywords`，写入 `shared.planning.user_keywords`（按用户提供原意归档）
	- 若用户选择关键词模式，世界观/人设/大纲必须优先吸收关键词，不得忽略核心约束
	- 段落字段仅生成文本相关：`text`、`next`、`speaker`（可选）
	- 同段分步显示仅使用 `display_break_lines`（可选，按原文行号断点）
	- 可生成 `speaker` 作为文本标注，但不生成图片路径字段

4. 自检并修复：
	- 所有 `next`（若存在）必须指向存在段落 ID
	- 不生成交互跳转字段（如 `choices`）
	- 若生成 `display_break_lines`，断点值必须为递增整数且落在 `1 <= n < 行数`
	- 若段落 `effect` 为 `typewriter` 且包含 `speed`，统一使用固定值 `55`
	- `shared.planning` 字段完整（`requirements_summary`、`worldview`、`characters`、`outline`、`script_form`、`planning_source`）
	- 若 `planning_source=user_keywords`，`shared.planning.user_keywords` 不得缺失
	- 不输出注释，不输出图片/演出字段

5. 写入文件并输出摘要：
	- 文件路径、脚本类型、段落数、是否为基础剧本
	- 世界观/人设/大纲/剧本是否已覆盖
	- 大纲来源模式（`ai_auto` / `user_keywords`）与关键词吸收情况
	- `shared` 读写情况（读取了哪些字段、写入了哪些字段）
	- 原创性声明（未参考项目内其他剧本正文）

## 规划包输出模板（用于编排阶段1）

```json
{
	"shared": {
		"planning": {
	"requirements_summary": "...",
	"script_form": "visual_novel",
	"planning_source": "ai_auto",
	"worldview": "...",
	"characters": [
		{ "name": "林澈", "profile": "..." }
	],
	"outline": [
		{ "chapter": 1, "summary": "..." }
	],
	"user_keywords": {
		"worldview": ["废土", "高塔城"],
		"characters": ["失忆女主", "机械师导师"],
		"outline": ["试炼", "背叛", "真相反转"]
	}
		}
	}
}
```

## 默认值（用户未指定时）

- 新建脚本默认采用视觉小说线性结构
- 剧本文本默认第三人称叙述 + 关键段落可带对话
- 未指定剧本形态时，默认视觉小说（`visual_novel`）
- 未指定大纲来源时，默认 `planning_source=ai_auto`

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