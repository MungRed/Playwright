---
name: generate-novel
description: 独立执行小说模块：基于需求生成完整小说并维护 planning 数据。关键词：novel, full text, planning, module1
---

## 职责

仅负责模块1：生成完整小说。

- 输入：主题、风格、人设、世界观约束
- 输出：`scripts/<script_name>/drafts/novel_full.md`
- 数据回写：`shared.planning` 与 `shared.pipeline_state`

不负责剧本 JSON 转换，不负责分镜与生图。

## 文档先行（必须）

执行前先确认小说模块文档已包含：
- 输入
- 输出
- 验收标准

## 关键约束

1. 小说正文必须通过混元生文 API 生成。
2. 长篇任务优先使用 `session_id + use_session_history=true`。
3. `context_files` 仅使用 `.txt`。
4. 写回 `script.json` 时，必须先读取完整 `shared`，仅更新目标字段。
5. 长文本禁止单次整篇生成；必须按“章节分批”调用生文 API（至少 2 批）。
6. 任一批次超时后，必须在同一 `session_id` 下缩短目标字数并续写，不可直接终止整任务。

## 执行流程

1. 读取 `script.json`（若不存在则初始化最小结构）。
2. 收集小说生成输入（主题、人物、风格、长度目标）。
3. 先生成章节计划（章标题 + 每章目标字数 + 关键事件）。
4. 按章分批调用混元生文 API 生成正文：
	- 固定同一 `session_id`
	- `use_session_history=true`
	- 单批建议控制在 1200-1800 字
5. 若某批超时，按“减半字数目标 + 续写提示”重试该批次，最多 3 次。
6. 合并各批正文后落盘 `novel_full.md`，并同步更新 `shared.planning` 与 `shared.pipeline_state`。
7. 输出小说模块验收结论（含分批次数与超时重试统计）。

## 输出

- 完整小说路径
- `shared.planning` 关键字段摘要
- `shared.pipeline_state` 更新摘要
- 分批生成摘要（批次数、成功率、超时重试次数）
- 失败时提供 `重试 / 降级 / 终止` 选项