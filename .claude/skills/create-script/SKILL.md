---
name: create-script
description: 生成世界观、人设与剧本文本，并可输出仅文本的基础剧本 JSON；不负责图片与资源回写。关键词：世界观, 人设, 剧本, 文本, 分支, 线性, story, script
---

## 功能说明

用于生成或改写“纯文本层”内容：
- 需求澄清结果（用户偏好摘要）
- 世界观设定
- 角色设定（人设）
- 剧本大纲
- 剧本段落文本（线性或分支）

本 skill **不负责**：`background.image`、`character_image` 回写、视觉演出参数与生图流程。

## 执行步骤

1. 确认任务范围：
	- 新建文本内容（世界观/人设/剧本）或修改现有文本内容
	- 若涉及 JSON 文件，先读取并定位目标段落 ID / 数组索引

2. 最少必要提问（仅缺失时提问）：
	- 用户希望的剧本形态：少选项小说 / 多选项文字冒险
	- 输出范围：仅世界观、仅人设、仅剧本，或三者组合
	- 是否先产出“规划包”（人设+大纲+形态）
	- 是否要求“基础剧本模式”（仅文本字段，不含任何资源路径）
	- 剧本结构：线性（`segments: []`）或分支（`start + segments: {}`）
	- `title`、`description`、目标篇幅与风格

3. 生成脚本结构（严格 JSON）：
   - 线性：`title`、`description`、`segments`（数组）
   - 分支：`title`、`description`、`start`、`segments`（对象）
	- 段落字段仅生成文本相关：`text`、`next`、`choices`、`speaker`（可选）
	- 可生成 `speaker` 作为文本标注，但不生成图片路径字段

4. 自检并修复：
	- 分支脚本中所有 `next` 必须指向存在段落 ID
	- `choices` 每项至少包含 `label` 与 `next`
	- 不输出注释，不输出图片/演出字段

5. 写入文件并输出摘要：
	- 文件路径、脚本类型、段落数、是否为基础剧本
	- 世界观/人设/大纲/剧本是否已覆盖

## 规划包输出模板（用于编排阶段1）

```json
{
	"requirements_summary": "...",
	"script_form": "novel_light_choices",
	"worldview": "...",
	"characters": [
		{ "name": "林澈", "profile": "..." }
	],
	"outline": [
		{ "chapter": 1, "summary": "..." }
	]
}
```

## 默认值（用户未指定时）

- 新建脚本默认采用线性结构
- 剧本文本默认第三人称叙述 + 关键段落可带对话
- 未指定剧本形态时，默认“少选项小说”（`novel_light_choices`）

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