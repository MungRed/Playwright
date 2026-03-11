# 三模块流水线契约（Doc-First）

## 1. 目标

将创作流程重构为三个主模块，且每个模块可独立运行并具备完整功能：
1. 小说模块（Novel Module）
2. 剧本模块（Script Module）
3. 图片资产模块（Image Asset Module）

本项目保持 agent-first，不新增专用 Python 流程编排脚本。

## 2. 模块定义

### 2.1 小说模块

- 输入：题材、风格、角色设定、世界观约束（可来自用户或 shared.planning）
- 输出：`scripts/<script_name>/drafts/novel_full.md` 与 `shared.planning`
- 验收标准：
  - 使用混元生文 API 生成
  - 长文本按章节分批生成（至少 2 批），禁止单次整篇请求
  - 超时后执行“同 session 续写 + 缩小批次”重试（最多 3 次）
  - 文本具备完整章节叙事（开端-发展-转折-收束）
  - 文本包含人物、环境、心理与对话混合叙事
  - `shared` 写回仅更新目标字段，保留其他字段

### 2.2 剧本模块

- 输入：`novel_full.md` 与剧本阶段文档约束
- 输出：`scripts/<script_name>/script.json`
- 验收标准：
  - 使用混元生文 API 生成
  - 按分镜分批生成 `storyboards -> scripts`（至少 2 批），禁止单次全量生成
  - 默认粒度为“一个分镜一次调用”，单次仅返回一个 `storyboard` 对象
  - 超时后执行“同 session 续写 + 缩小批次”重试（最多 3 次）
  - 段落结构线性可达，`id` 唯一
  - 旁白/对话混合：旁白占比 >= 40%（全局与分镜）
  - 旁白段 `character_image=null`，对话段具备可绑定立绘
  - `typewriter/speed` 约束满足（`speed=55`）
  - 单条 `text` 长度 <= 80
  - 固定执行质量闭环：本地门禁 -> 模型复评 -> 定向改写（最多 3 轮）
  - 本地质量门禁通过：`tools/check_script_quality.py --min-narration-ratio 0.45`
  - 本地修复工具可用：`tools/enrich_script_narration.py`、`tools/auto_refine_script.py`
  - 模型复评使用 0-10 分制；若 `overall_score >= 6.5`、`story_completeness >= 7`、`visual_novel_adaptation >= 7`、其余核心维度 >= 6，则可判定为 `pass_with_polish`
  - `shared.pipeline_state` 更新完整

### 2.3 图片资产模块

- 输入：`script.json`（已包含 `storyboards`）与资产风格约束（`shared.style_contract`）
- 输出：
  - 人设图、背景图、立绘等图片资产
  - `shared.asset_manifest`
- 验收标准：
  - 不再生成 `storyboard.json`，直接消费剧本内分镜生成图片
  - 人设图必须先文生图生成“三视图设定图”（正/侧/背）
  - 角色立绘必须基于三视图设定图走图生图，且输出竖版（推荐 `720x1280`）
  - 回写 `character_image` 的必须是竖版立绘，不可回写三视图设定图
  - 可独立产出图片资产 + 资产清单
  - 背景图显式无人物约束
  - `segment_id` 使用真实段落 id
  - `shared` 写回保留非目标字段

## 3. 编排约束

- 编排只做调度，不与模块内部逻辑耦合。
- 主编排 skill 只串联三个模块 skill。
- 其他 skill（如角色设定图、资产回写）归类为分镜模块辅助能力。

## 4. 实施清单

1. 拆分 `create-script` 为 `generate-novel` 与 `generate-script`。
2. 保留/强化 `generate-scene-assets` 作为分镜模块主 skill。
3. 更新 `orchestrate-script-production`，仅调用三主模块 skill。
4. 更新 `README.md`、`docs/DEVELOPMENT.md`、`.github/copilot-instructions.md`。
5. 更新 `.github/agents/doc-first-script-pipeline.agent.md` 与 `iterate-skills` 约束。

## 5. 当前状态

- 本文档创建时间：2026-03-11
- 状态：执行中（待完成 skill 拆分与全量引用清理）