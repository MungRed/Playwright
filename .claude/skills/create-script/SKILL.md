---
name: create-script
description: 生成世界观、人设与剧本文本（传统文本先行 + 本地转换 JSON）；不负责图片资产回写。关键词：世界观, 人设, 剧本, 视觉小说
---

## 目标

面向“文本层”创作，产出并维护：
- `shared.planning`（需求摘要/世界观/角色/大纲）
- `drafts/planning_draft.*`、`drafts/novel_draft.*`
- 基础 `script.json`（仅文本与演出字段，不含资产回写）

## 强约束（单一真相）

1. 阶段1/2文本必须调用 `mcp_playwright-im_generate_text` 生成。
2. 长篇必须使用 `session_id + use_session_history=true`。
3. 文件上下文只传 `.txt`（见 `PITFALLS.md §2.2`）。
4. 阶段2必须注入阶段1 `planning_draft` 全文（优先 `context_files`）。
5. 产物必须原创，不读取其他剧本正文做素材。
6. `display_break_lines` 为可选节奏手法；使用时必须是字符串数组且 `text=""`。
7. `effect` 为可选演出手法；若 `effect=typewriter`，`speed` 固定 `55`。
8. 写回后必须执行双门：
   - **结构门**：`python scripts/normalize_script_break_lines.py scripts/<script_name>/script.json --check`
   - **AI质量门**：`python scripts/quality_gate_ai.py scripts/<script_name>/script.json --check`

## 输入澄清（缺失才问）

- 剧本名、篇幅、风格、受众
- 大纲来源：`ai_auto` 或 `user_keywords`
- 若 `user_keywords`：补齐 `worldview/characters/outline`
- 是否阶段2后人工审稿：`review_after_stage2`

## 执行流程

1. 读取 `scripts/<script_name>/script.json`，获取/创建 `shared`。
2. 阶段1生文：生成规划草稿并保存 `planning_draft.md + planning_draft.txt`。
3. 解析规划并写入 `shared.planning`（保留 `shared` 其他字段）。
4. 阶段2生文：基于 `planning_draft` 生成正文草稿并保存 `novel_draft.md + novel_draft.txt`。
5. 本地转换为 `segments`：
   - 禁止 `text` 含 `\n`
   - 需要分步时使用 `display_break_lines`
6. 执行规范化脚本并通过 `--check` 门禁。
7. 执行本地质量体检：`quality_audit.py` 输出 `metrics/issues/rewrite_prompt`。
8. 若启用质量闭环：
   - 先用 `quality_audit.py` 的问题清单做定向改写
   - 再调用 `review-script` 做模型复评
   - 按门槛重写（最多2轮）

## 定向改写提示模板（直接可用）

- 文笔平：
  - “请重写以下段落，保留剧情事实不变，增强画面细节（视觉/听觉/触觉）与句式变化，避免口号化表达。”
- 角色同质化：
  - “请将角色A与角色B的说话方式区分开：A偏___，B偏___；每段至少体现一处角色专属动作/语气。”
- 节奏拖沓：
  - “请把该段拆为2-3个信息步，采用‘引子→冲突→推进’结构；关键句放在每步末尾。”
- 纯对白：
  - “在不改变对白内容前提下，补充环境镜头、人物动作与心理活动，形成‘叙述+对白’混合段落。”。

## 最低输出要求

- 文件路径：`script.json`、`planning_draft.*`、`novel_draft.*`
- 统计信息：段落数、`changed_segments`、质量门禁状态
- 共享数据：`shared.planning` 与 `shared.pipeline_state` 更新摘要

## 快速自检清单

- `shared.planning` 是否完整（含 `planning_source`）
- `segments` 是否线性可达（`next` 合法）
- `display_break_lines` 使用处是否满足结构规则
- `typewriter` 段落是否 `speed=55`
- `normalize_script_break_lines.py --check` 是否返回 `changed_segments=0`
- `quality_audit.py --check` 是否通过
