---
name: orchestrate-script-production
description: 串联剧本生产三模块（小说→剧本→图片资产）的纯 agent 编排 skill，强调文档先行与模块解耦。关键词：pipeline, orchestration, doc-first, agent-first
---

## 职责边界

仅负责阶段编排与门禁，不直接写长篇正文或替代子 skill 的职责。

## 三模块编排

1. 模块1 小说
   - 调用 `generate-novel` 生成完整小说
   - 维护 `shared.planning` 与小说路径
2. 模块2 剧本
   - 调用 `generate-script` 从完整小说生成 `script.json`
   - 生成策略固定为“一个分镜一次调用”，避免长输出超时
   - 调用 `configure-script-presentation`（可选）补演出字段
   - 固定执行“本地门禁 -> 模型复评 -> 定向改写”的闭环
   - 调用 `review-script` 做质量门禁，并以 `delivery_gate` 作为编排停止条件
3. 模块3 图片资产
   - 调用 `generate-scene-assets` 基于剧本内分镜生成图片资产（人设图/背景图/立绘）与资产清单
   - 模块3生图顺序固定为：三视图人设图 -> 图生图竖版立绘 -> 资产映射
   - 需要回写时再调用 `attach-script-assets`

## 文档先行规则（必须）

- 每模块开始前先确认模块文档已更新（输入/输出/验收标准）。
- 每模块完成后更新模块结论与下一模块前置条件。
- 同步维护 `docs/DEVELOPMENT.md` 的变更记录。

## 全局约束

- 流程编排必须由 agent 执行，禁止新增专用 Python 流程脚本。
- 文本生成必须走混元生文 API。
- `shared` 是唯一共享数据源，写回必须保留非目标字段。
- 任一门禁失败必须中断后续阶段。
- 长文本阶段（模块1/2）默认采用分批生成，禁止单次超长请求。
- 出现超时时，必须优先执行“同会话续写 + 缩小批次”重试策略，再考虑模型降级。
- 模块2默认最多 3 轮质量闭环；未达到停止条件前不得进入模块3。

## 模块2质量闭环（固定）

1. 生成初稿后执行 `tools/check_script_quality.py --min-narration-ratio 0.45`。
2. 若本地门禁失败，优先执行：
   - `tools/enrich_script_narration.py`
   - `tools/auto_refine_script.py`
3. 本地门禁通过后调用 `review-script`。
4. 若 `delivery_gate=rewrite_needed`，则依据 `weaknesses/suggestions` 执行定向改写后重跑第 1-3 步。
5. 若 `delivery_gate=pass` 或 `pass_with_polish`，则模块2完成。

## 模块2停止条件（必须）

满足以下任一条件，才允许进入模块3：

1. `review-script.delivery_gate=pass`
2. `review-script.delivery_gate=pass_with_polish`

若达到最大轮数后仍未满足上述条件，则中止在模块2，并输出失败摘要与下一轮优先修复项。

## 超时应对策略（模块1/2）

1. 固定 `session_id`，并启用 `use_session_history=true`。
2. 首次按中等批次请求；若超时则将该批目标规模下调 30%-50%。
3. 同一批次最多重试 3 次；超过上限时返回 `重试 / 降级 / 终止`。
4. 将分批与重试结果写入 `shared.pipeline_state`（建议字段：`chunk_rounds`、`timeout_retries`）。

## 输出口径

- `script_name`
- 当前阶段与结果
- 关键产物路径（novel_full.md、script.json）
- `shared.asset_manifest` 条目数
- 质量门禁结论
- 模块2闭环摘要（轮次数、最终 `delivery_gate`、停止原因）
- 下一步建议（继续/重试/人工审阅）
