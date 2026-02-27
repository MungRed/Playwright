---
name: create-script
description: 为文字冒险项目创建或更新游戏脚本（JSON），支持线性与分支结构。关键词：script, json, 剧本, 分支, 线性, choices, segments
---

## 功能说明

用于在 `scripts/` 下创建或修改游戏脚本，输出可直接被引擎加载的 JSON。

## 执行步骤

1. 读取并确认脚本目标：
	- 新建脚本：确认文件名（如 `午夜密室.json`）
	- 修改脚本：读取现有文件并定位要改的段落

2. 在生成前询问最少必要信息：
	- 脚本类型：线性（`segments: []`）或分支（`start + segments: {}`）
	- 标题与简介：`title`、`description`
	- 风格与长度：短篇/中篇；偏悬疑/奇幻/恐怖等

3. 生成脚本结构（严格 JSON）：
	- 线性：`title`、`description`、`segments`（数组）
	- 分支：`title`、`description`、`start`、`segments`（对象）
	- 段落字段仅使用：`text`、`effect`、`speed`、`next`、`choices`

4. 自检并修复：
	- 分支脚本中所有 `next` 都必须指向存在的段落 ID
	- `choices` 至少含 `label` 与 `next`
	- 不输出注释，不输出无效字段

5. 写入文件并给出结果摘要：
	- 文件路径
	- 脚本类型
	- 段落数量 / 分支数量

## 默认值（用户未指定时）

- `effect`: `fadein`
- `speed`: `30`
- 新建脚本默认采用线性结构

## 示例（最小线性脚本）

```json
{
  "title": "迷雾车站",
  "description": "一个发生在深夜车站的短篇故事",
  "segments": [
	 {"text": "午夜时分，你独自站在空荡站台。", "effect": "fadein", "speed": 30},
	 {"text": "远处传来列车鸣笛，雾气逐渐逼近。", "effect": "typewriter", "speed": 55}
  ]
}
```