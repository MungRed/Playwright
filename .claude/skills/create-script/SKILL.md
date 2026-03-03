---
name: create-script
description: 生成世界观、人设与剧本文本，采用“传统文本先行 + 本地转换 JSON”流程；不负责图片与资源回写。关键词：世界观, 人设, 剧本, 文本, 视觉小说, story, script
---

## 功能说明

用于生成或改写“纯文本层”内容（先生成传统文本，再转换为 JSON）：
- 需求澄清结果（用户偏好摘要）
- 世界观设定
- 角色设定（人设）
- 剧本大纲
- 剧本段落文本（视觉小说线性叙事）

本 skill **不负责**：`background.image`、`character_image` 回写、视觉演出参数与生图流程。

## 生成方式约束（必须执行）

- 从现在起，世界观/人设/大纲/剧本文本的 AI 生成必须通过混元生文 API 完成。
- 必须调用 MCP 生文工具：`mcp_playwright-im_generate_text`（对应 ChatCompletions）。
- 长篇任务必须优先使用 `session_id` + `use_session_history=true` 保留多轮上下文，避免每轮只靠单条 prompt。
- 当上下文过长时，必须改用 `context_files`（本地路径或 URL）上传到混元文件接口，并通过消息 `FileIDs` 参与对话；文件对话建议开启 `enable_deep_read=true`。
- 会话续写建议保持 `carry_forward_file_ids=true`（默认），后续轮次可自动继承最近历史 `FileIDs`，减少重复传文件。
- 禁止在未调用生文 API 的情况下直接由模型“离线脑补”产出完整剧本正文。
- 禁止要求生文 API 直接输出完整 `script.json`（包含 `segments` 的结构化 JSON）。
- 生文 API 产物必须优先采用传统文本形态（叙事正文/章节体），再由 agent 在本地转换为 JSON。
- 阶段2 `novel_draft` 写作风格必须为“叙事+对话混合”，禁止全篇纯对白：必须包含人物动作描写、环境描写与心理描写。
- 默认参考文章为《铁道银河之夜》：仅可提取主题气质、意象密度与叙事节奏，不得复刻原文句式、角色命名、专有设定与关键情节。
- 允许在调用前后做结构化处理（提示词拼装、字段校验、JSON 转换修复），但创作文本本体必须来自生文 API 返回。

## 草稿落盘约束（必须执行）

- 阶段1/2 的生文原文必须先落盘保存，再进行 JSON 转换。
- 目录约定：`scripts/<script_name>/drafts/`。
- 推荐文件：
	- 阶段1规划草稿：`planning_draft.md`
	- 阶段2正文草稿：`novel_draft.md`
- 可在 `shared.pipeline_state` 写入 `planning_draft_path`、`novel_draft_path` 便于追踪。
- 生成 `novel_draft.md` 前，必须读取 `planning_draft.md` 并将其内容注入生文提示词上下文（建议全文传入）。
- 若 `planning_draft.md` 全文 + 已生成正文超出单次消息预算，必须将两者作为 `context_files` 上传后续写，禁止仅传“任务：续写xx段”而不附前文。

## 原创约束（必须执行）

- 创作世界观/人设/剧情文本时，禁止参考项目中已有剧本正文（`scripts/*/script.json`）作为素材来源。
- 仅允许读取“当前目标脚本文件”用于续写、改写或结构修复；禁止从其他剧本抽取设定、情节、对白、命名。
- 用户若明确要求“仿照某现有剧本”，应拒绝照搬并改为提供同题材但全新设定与情节。
- 输出文本必须保证原创，不得出现对仓库现有剧本可识别的段落复用或近似改写。

## 共享数据读写（必须执行）

- 统一从 `scripts/<script_name>/script.json` 顶层 `shared` 读取上下文。
- 阶段1产物必须写入 `shared.planning`。
- 若历史脚本存在顶层 `planning` 但无 `shared.planning`，需先兼容读取，并在写回时迁移到 `shared.planning`。
- 写回时保留 `shared` 其他字段（如 `style_contract`、`character_refs`、`asset_manifest`）。

## 执行步骤

1. 确认任务范围：
	- 新建文本内容（世界观/人设/剧本）或修改现有文本内容
	- 若涉及 JSON 文件，先读取并定位目标段落 ID / 数组索引
	- 若为新建创作，禁止读取其他 `scripts/*/script.json` 作为创意参考

2. 按缺失信息提问（仅缺失时提问）：
	- 用户希望的剧本形态：视觉小说（线性叙事）
	- 大纲来源：`AI 自动生成` 或 `用户提供关键词`
	- 若选择“用户提供关键词”，补齐：世界观关键词、人物设定关键词、剧情大纲关键词（可分别提供）
	- 输出范围：仅世界观、仅人设、仅剧本，或三者组合
	- 是否先产出“规划包”（人设+大纲+形态）
	- 是否要求“基础剧本模式”（仅文本字段，不含任何资源路径）
	- 参考文章（默认《铁道银河之夜》；仅作风格参考，不做复写）
	- 剧本结构：线性（`segments: []`）
	- `title`、`description`、目标篇幅与风格

3. 生成与转换（两阶段）：
	- 先组织生文提示词，调用 `mcp_playwright-im_generate_text` 生成传统文本：
		- 规划草稿（需求摘要/世界观/人物/大纲）
		- 正文草稿（传统小说或剧本对白体，不含 JSON 结构）
	- 生成正文草稿时，必须把阶段1 `planning_draft` 作为输入上下文一并传给生文 API，确保设定与叙事一致。
	- 对于分批续写，必须复用同一 `session_id`；每批完成后将 assistant 产物并入会话历史，再发下一批。
	- 对于分批续写，若首批已使用 `context_files`，后续批次保持 `carry_forward_file_ids=true`，避免文件上下文丢失。
	- 同一篇正文的连续分批续写，提示词默认要求“自然承接前文场景与情绪曲线”，不得强制“每批段尾留悬念”；仅在用户明确要求章节钩子时才添加悬念约束。
	- 正文草稿中需显式体现视觉小说叙事层：
		- 人物描写（动作/神态/语气）
		- 环境描写（场景、时间、氛围）
		- 心理描写（当下动机、情绪变化）
	- 对话仅作为叙事组成部分，不得占满全部段落。
	- 先将草稿落盘到 `scripts/<script_name>/drafts/*.md`
	- 再由 agent 本地解析草稿并转换到剧本 JSON 结构
	- 视觉小说标准结构：`title`、`description`、`segments`（数组）
	- 顶层确保存在 `shared`，并写入/更新 `shared.planning`
	- `shared.planning` 必须写入 `planning_source`：`ai_auto` 或 `user_keywords`
	- 若 `planning_source=user_keywords`，写入 `shared.planning.user_keywords`（按用户提供原意归档）
	- 若用户选择关键词模式，世界观/人设/大纲必须优先吸收关键词，不得忽略核心约束
	- 段落字段仅生成文本相关：`text`、`next`、`speaker`（可选）
	- 同段分步显示仅使用 `display_break_lines`（可选，按原文行号断点）
	- 可生成 `speaker` 作为文本标注，但不生成图片路径字段

4. 自检并修复：
	- 草稿文件存在且可读取（阶段1/2）
	- 阶段2生文调用日志/提示词中可追溯 `planning_draft` 已被注入（或在产物记录中体现该输入来源）
	- 阶段2正文草稿不得为“全段均是 角色名：台词”格式；若检测为纯对白，必须重生文。
	- 所有 `next`（若存在）必须指向存在段落 ID
	- 不生成交互跳转字段（如 `choices`）
	- 若生成 `display_break_lines`，断点值必须为递增整数且落在 `1 <= n < 行数`
	- 若段落 `effect` 为 `typewriter` 且包含 `speed`，统一使用固定值 `55`
	- `shared.planning` 字段完整（`requirements_summary`、`worldview`、`characters`、`outline`、`script_form`、`planning_source`）
	- 若 `planning_source=user_keywords`，`shared.planning.user_keywords` 不得缺失
	- 不输出注释，不输出图片/演出字段

5. 写入文件并输出摘要：
	- 草稿路径、脚本路径、脚本类型、段落数、是否为基础剧本
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
	"reference_article": {
		"title": "铁道银河之夜",
		"usage": "theme_tone_only"
	},
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
- 剧本文本默认第三人称叙述，强制包含人物/环境/心理描写，并在关键段落插入对话
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