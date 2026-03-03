---
name: orchestrate-script-production
description: 串联剧本生产四阶段（规划→文本→人设图→场景资产回写）的编排 skill。关键词：pipeline, orchestration
---

## 职责边界

仅负责“阶段编排与门禁”，不直接手写长文本正文。

## 四阶段流水线

1. **阶段1 规划**
   - 调用 `create-script` 生成 `planning_draft.*`
   - 写入 `shared.planning`
2. **阶段2 文本剧本**
   - 注入 `planning_draft` 全文，生成 `novel_draft.*`
   - 转换 `script.json`（文本+演出字段）
   - 执行结构门禁：
     - `python scripts/normalize_script_break_lines.py scripts/<script_name>/script.json`
     - `python scripts/normalize_script_break_lines.py scripts/<script_name>/script.json --check`
   - 执行质量门禁：
     - `python scripts/quality_audit.py scripts/<script_name>/script.json --check`
3. **阶段3 人设图**
   - 调用 `generate-character-images` 写入 `shared.character_refs`
4. **阶段4 场景与回写**
   - 调用 `generate-scene-assets` 生成 `shared.asset_manifest`
   - 调用 `attach-script-assets` 回写 `background/character_image`

## 全局规则（必须）

- 文本生成必须走混元生文 API。
- 禁止读取其他剧本正文作为创作素材。
- `shared` 为唯一共享数据源，读写必须保留其他字段。
- `display_break_lines` 可选；使用时必须结构合法。
- `effect` 可选；若 `typewriter` 则 `speed=55`。
- 任一门禁失败必须中断后续阶段，不得“带病进入下一阶段”。

## 关键门禁

### 阶段2结束前
- 结构门禁通过（`--check` 返回 `changed_segments=0`）
- 本地质量门禁通过（`quality_audit.py --check`）
- 标题一致性：`title == 文件名`
- 模型质量门禁（启用时）：
  - `overall_score>=6.8`
  - `literary_quality>=6`
  - `character_development>=6`
  - `creativity_theme>=6`

## 质量迭代顺序（固定）

1. 本地体检：`quality_audit.py --check`
2. 若失败：按 `suggestions.rewrite_prompt` 定向改写
3. 模型复评：`review-script` 严格模式
4. 若仍未达标：回到步骤2（最多2轮）

### 审稿分支
- `review_after_stage2=true`：暂停并等待用户确认
- `review_after_stage2=false`：通过门禁后自动进入阶段3/4

## 失败处理

- API失败/限流/上下文上传失败：停止链路并给出 `重试 / 降级 / 终止` 选项。
- 图生图失败：不自动跳过，先询问用户策略。

## 结果输出（统一口径）

- `script_name`、阶段状态、草稿路径
- `review_after_stage2` 与最终 `review_gate`
- 质量门禁结果（如启用）
- 资产生成统计（背景数/立绘数/复用数）
- 最终剧本路径
