# 开发文档（Development Guide）

## 1. 文档目标

本文件用于记录项目的开发规范、架构约定与关键变更。
任何涉及代码行为、结构、配置或运行方式的改动，都应同步更新本文件。

---

## 2. 项目定位

本项目是基于 `Python + pygame` 的本地**剧本阅读器**，核心能力：
- 加载 `scripts/<script_name>/script.json` 剧本
- 支持线性阅读
- 支持多种文字演出效果
- 提供左侧进度栏（进度与当前段落）
- 支持段落背景图（渐变/震动）与右侧人物立绘展示

---

## 3. 目录与职责

- `main.py`：程序入口，启动 pygame 应用
- `engine/pygame_app.py`：主菜单与阅读主循环（事件、渲染、状态机）
- `.mcp/image_gen_server.py`：MCP 服务，封装腾讯混元生文（ChatCompletions）与生图（TextToImageLite / SubmitTextToImageJob）
- `scripts/<script_name>/script.json`：剧本数据（视觉小说线性叙事）
- `scripts/<script_name>/assets/*`：该剧本的背景图与人物图资源
- `scripts/<script_name>/review.json`：剧本评分报告（可选，由 `review-script` skill 生成）
- `scripts/bootstrap_env.py`：本地环境检查与初始化

---

## 4. 运行与开发

### 4.1 初始化环境（推荐）

```bash
python scripts/bootstrap_env.py
```

该脚本会自动：
- 创建虚拟环境 `.venv`
- 安装所有依赖（包括 pygame）
- 验证环境配置

仅检查：

```bash
python scripts/bootstrap_env.py --check-only
```

---

## 5. 剧本数据约定

### 5.0 资源目录约定

- 项目结构统一为“每个剧本一个目录”：`scripts/<script_name>/script.json` + `scripts/<script_name>/assets/`。
- MCP 生图工具支持 `script_name` 入参，默认落盘到 `scripts/<script_name>/assets/`。
- 剧本中的 `background.image` / `character_image` 建议使用相对路径：`assets/<filename>.png`。
- 人物设定图（`char_ref_*`）用于风格与角色一致性参考，不直接绑定到 `character_image`。
- 剧本绑定的人物图应使用剧情立绘（如 `char_<name>_<mood>.png`）。
- 生图服务会在剧本资源目录维护 `scripts/<script_name>/assets/_style_contract.json` 作为风格契约缓存（style/negative 锚点）。
- 文本生产新增草稿落盘约定：阶段1/2 生文原文先保存到 `scripts/<script_name>/drafts/`，再由 agent 转换为 `script.json`。
- 推荐草稿文件：`planning_draft.md`（规划）、`novel_draft.md`（正文）。
- 一致性约束：阶段2生成 `novel_draft.md` 时，生文请求必须注入 `planning_draft.md` 内容（优先全文）作为上下文，避免前后文设定漂移。
- 文风约束：阶段2 `novel_draft` 必须包含人物描写、环境描写与心理描写，并与对话混合；禁止全篇纯对白。- 剧本评分报告：`scripts/<script_name>/review.json` 由 `review-script` skill 生成，包含多维度评分、优缺点分析与改进建议；不影响剧本运行。
### 5.1 线性格式

- `segments` 为数组
- 系统会自动补 `next` 链（当段落无 `next` 时）

### 5.2 常用字段

- `shared`: 剧本流水线共享数据容器（推荐）
- `text`: 段落正文。若同段有 `display_break_lines`，本字段留空 `""`（引擎不读）。
- `display_break_lines`: 同段分步文本数组（字符串格式）。每项为**该步新增的一行文本**（非累积存储），引擎按顺序累积拼接后渲染。`text` 留空可避免内容重复。
- `effect`: `typewriter | shake`
- `speed`: 动画速度（ms/帧），其中 `typewriter` 固定为 `55`
- `next`: 下一段 ID
- `speaker`: 可选说话人元数据（当前 UI 不单独显示姓名）
- `character_image`: 人物图路径（相对项目根目录或绝对路径）
- `background`: 背景配置对象

### 5.3 共享数据协议（shared）

- 顶层建议使用 `shared` 作为流水线单一共享数据源。
- 推荐由各阶段按最小改动读写：
	- `shared.planning`：阶段1需求摘要、世界观、人设、大纲、剧本形态（`visual_novel`）
		- 支持大纲来源字段：`planning_source`（`ai_auto` / `user_keywords`）
		- 可选参考文章字段：`reference_article`（默认《铁道银河之夜》），建议写入 `usage=theme_tone_only`
		- 当 `planning_source=user_keywords` 时，建议写入 `user_keywords`（`worldview`/`characters`/`outline`）
	- `shared.style_contract`：双锚点画风约束
		- `background_style_anchor` / `background_negative_anchor`
		- `character_style_anchor` / `character_negative_anchor`
	- `shared.character_refs`：人物设定图路径清单
	- `shared.asset_manifest`：段落资产映射（`segment_id`、`background_image`、`character_image`）
	- `shared.pipeline_state`：阶段进度与统计信息
		- 建议包含审稿分支字段：`review_after_stage2`（是否阶段2后审稿）与 `review_gate`（`pending_user_review|auto_continue|approved|regenerate_stage2`）
		- 建议包含质量门禁字段：`quality_round`（当前重写轮次）、`quality_gate`（`pass|rewrite_pending|max_round_reached`）、`quality_scores`（最近一次评分摘要）
- 兼容历史脚本：若仅有顶层 `planning`，可读取后迁移到 `shared.planning`。
- 默认约定：用户未指定大纲来源时，`planning_source=ai_auto`。
- 编排执行约定：阶段1（规划）需先确认 `review_after_stage2` 偏好；阶段2完成后，若为 `true` 则先暂停等待用户审稿并按反馈重生成或继续，若为 `false` 则自动连续执行阶段3-4。
- 一致性约定：`title` 应与剧本文件名（不含 `.json`）保持一致；不一致时应自动修正。

### 5.4 背景配置（background）

- `image`: 背景图路径（推荐放 `assets/`，相对 `script.json`）
- `effects`: 背景效果数组，支持 `fade` 与 `shake`
- `fade_ms`: 背景切换渐变时长（毫秒）
- `shake_ms`: 背景震动持续时长（毫秒）
- `shake_strength`: 背景震动强度（像素）

---

## 6. UI 架构约定

### 6.1 阅读页布局

- 左侧：进度栏（仅展示阅读进度与当前段落）
- 中间：阅读主区（固定 `1280x720`，背景层 + 正文直出）
- 右侧：人物栏（立绘显示 + 操作提示）
- 窗口策略：主菜单固定 `1280x720`；进入阅读后窗口扩展为“左栏 + 中间阅读区 + 右栏”，且左右栏位于中间阅读区外侧（最小宽度 `220 + 1280 + 260`）。
- 主菜单剧本列表支持滚动浏览：当剧本数量超过可视卡片数时，可使用鼠标滚轮或键盘 `↑/↓` 滚动，右侧显示滚动条。

### 6.2 背景图渲染约定

- 背景图使用 cover 策略适配中间阅读区尺寸（保持比例并居中裁切）。
- 背景切换按段落配置执行渐变；惊吓段可配置震动。
- 图像分为原图缓存与缩放缓存，窗口尺寸变化时清理缩放缓存并重建。
- 渲染顺序固定为：背景 → 侧栏 → 文本覆盖层，避免整体闪烁。

### 6.3 文本可读性约定

- 正文区域不叠加底板，使用黑色描边突出文字并保留完整背景。
- 文本覆盖渲染在中间阅读区左上角内边距区域，自上向下排版。
- 中间阅读区不显示剧本标题、操作提示与人物名。
- 右侧人物栏仅显示立绘；操作提示位于右栏下半区域。
- 段内换行优先通过“行间距”呈现，不依赖 `\n\n` 空白行制造视觉间隔。

### 6.4 段内分步推进约定

- 同一段通过 `display_break_lines`（字符串数组）配置分步显示：每项为该步**新增的一行文本**，引擎按步累积拼接后渲染。
- `text` 字段在有 `display_break_lines` 时留空 `""`，避免内容重复造成 JSON 过大。
- 编排剧本时不在 `text` 中写 `\n`；分行控制完全由 `display_break_lines` 数组顺序决定。
- 单步动画播放期间再次空格/左键为“跳过当前步动画并直接显示完整步”。
- 当前段最后一步显示完成后，下一次空格/左键才进入下一段。
- 同段后续步骤采用“追加显示”策略，不重复从首字符重播整步动画。
- 动画阶段与静态阶段均使用黑色描边文字渲染，以保持视觉一致性。
- 引擎不自动按句切分；未配置分步字段时默认整段一次显示。

---

## 7. 配置与安全

### 7.1 MCP 配置（双轨制）

本项目支持两种 AI 编辑环境，各有独立的 MCP 配置文件：

| 环境 | 配置文件 | 模板文件 | 用途 |
|------|---------|---------|------|
| **VSCode 扩展** | `.vscode/mcp.json` | `.vscode/mcp.example.jsonc` | VSCode 内置的 Copilot/插件调用 |
| **Claude Code CLI** | `.mcp.json` | `.mcp.example.json` | Claude Code 对话中直接调用 MCP 工具 |

**配置约定**：
- 两个配置文件均已在 `.gitignore` 中忽略，不会提交到版本库
- 新成员拉取后需从模板文件复制并填写真实密钥
- 可运行 `python scripts/bootstrap_env.py` 自动从模板生成本地配置
- **关键区别**：
  - VSCode 配置使用 `${workspaceFolder}` 变量，格式为 `servers` 对象
  - Claude Code 配置使用相对路径，格式为 `mcpServers` 对象

**快速初始化**：
```bash
# 自动生成两个配置文件
python scripts/bootstrap_env.py

# 然后分别编辑填写密钥
# .vscode/mcp.json - VSCode 扩展用
# .mcp.json - Claude Code CLI 用
```

### 7.2 API 提供商与接口约定

- AI 提供商：仅 `hunyuan`（腾讯混元）
- 生文按腾讯云官方 `ChatCompletions` 调用（Endpoint: `hunyuan.tencentcloudapi.com`，版本 `2023-09-01`）
- 生图按腾讯云官方 `TextToImageLite / SubmitTextToImageJob` 调用
- 生文默认模型由 `HUNYUAN_TEXT_MODEL` 控制，生图接口域名由 `HUNYUAN_ENDPOINT` 控制
- 生文 MCP 工具 `generate_text` 新增会话与文件上下文参数：`session_id`、`use_session_history`、`context_files`、`enable_deep_read`，并支持 `carry_forward_file_ids` 自动继承历史 `FileIDs`，用于长篇续写稳定保留上下文。
  - **`enable_deep_read` 注意**：深度阅读功能默认未开通，必须传 `enable_deep_read=false`；传 `true` 会触发 `InvalidParameter` 报错。
  - **`context_files` 文件格式限制**：混元文件上传接口仅接受 `.txt` 格式，不支持 `.md`；上传前须将草稿另存为 `.txt`。
- 同一 `session_id` 新增并发保护：服务端按会话文件锁串行化读写，避免并发请求造成历史未落盘；锁等待超时会返回明确错误并提示改串行调用。
- 生文上下文文件采用混元 `FilesUploads` 上传后，通过消息 `FileIDs` 挂载到 user 消息；本地文件可复用 COS 自动上传链路（需 `COS_AUTO_UPLOAD_ENABLED=true`）。
- 会话历史默认持久化到 `scripts/shared/text_sessions/<session_id>.json`，并按 40 条消息上限自动裁剪旧消息（优先保留 system）。
- 剧本文本生产约束：阶段1/2（规划与正文）必须通过生文 API 生成，不允许跳过 API 直接离线产出完整文本。
 2026-03-03：`generate_text` 新增 `carry_forward_file_ids`（默认 true），会话续写时可自动继承最近 user 消息中的 `FileIDs`，减少重复传 `context_files`。
- 生图服务默认支持质量稳定化参数：`scene_type`、`style_anchor`、`negative_anchor`、`enforce_style`、`strict_no_people`、`retry_max`。
- 生图服务默认支持退避重试：`HUNYUAN_RETRY_MAX`、`HUNYUAN_RETRY_BASE_SEC`。
- `TextToImageLite` 会做分辨率归一化以降低失败率：横图→`1280x720`、竖图→`720x1280`、方图→`1024x1024`。
- 提示词策略要求：允许长提示词，推荐按“主体要素 + 构图镜头 + 光照色调 + 材质细节 + 用途约束”分层描述；背景需增加文本可读区留白约束，立绘需增加表情强度与边缘清晰度约束。
- 图生图支持本地参考图自动上传 COS：当启用 `COS_AUTO_UPLOAD_ENABLED=true` 且 `reference_images` 传本地路径时，服务会先按内容哈希 Key 检查对象是否已存在，存在则直接复用 URL，不存在再上传后回填 URL。
- COS 自动上传依赖：`cos-python-sdk-v5`（通过 `.mcp/requirements.txt` 安装）。
- 剧情立绘约定：立绘阶段强制使用图生图（`SubmitTextToImageJob` + `reference_images`），且输出为竖向分辨率（推荐 `720x1280`）。
- 图生图失败处理：限流/参考图不可访问/任务超时时，必须中断自动流程并询问用户“重试 / 降级 / 终止”。

---

## 8. 变更维护规则（必须）

当发生以下任一变更时，必须更新本文件：
- 新增/删除模块文件
- 调整主流程或交互行为
- 修改配置文件名、路径、环境初始化方式
- 变更剧本 JSON 约定或字段语义

更新要求：
- 只更新受影响章节，保持精确聚焦
- 术语与命名必须与代码一致
- 不写泛化描述，写清“改了什么、影响哪里”
- `9.1 最近 12 条` 超出 12 条时，自动处理最旧条目：
	1) 若仍具长期参考价值（协议、架构、流程里程碑），迁移到 `9.2 长期里程碑`；
	2) 若仅为短期过程细节，直接移除，不进入长期里程碑。

---

## 9. 最近变更记录

### 9.1 最近 12 条
- 2026-03-04：调整 Git 忽略策略：`scripts/*/` 继续统一忽略剧本实例目录，且不再保留 `scripts/shared/**` 的跟踪例外；`scripts/shared` 作为本地运行缓存目录默认不纳入版本控制。
- 2026-03-03：落地“写作质量闭环”：阶段2新增严格评审与硬门槛（`overall_score/literary_quality/character_development/creativity_theme`），不达标触发定向重写并复评（最多2轮）；在 `shared.pipeline_state` 新增 `quality_round/quality_gate/quality_scores` 建议字段。
- 2026-03-03：新增 `review-script` skill，用于调用腾讯混元大模型对剧本进行多维度评分与分析，输出改进建议并保存到 `scripts/<script_name>/review.json`；评分维度包括故事完整性、角色塑造、文学质量、视觉小说适配度与创意主题；支持单剧本或批量评测。
- 2026-03-03：根据银河铁道之夜制作踩坑经验，批量更新四个 skill：① `create-script`：`display_break_lines` 改为字符串数组、`text` 留空、JSON 写入必须用 `json.dumps`、自检不再校验整数断点；② `configure-script-presentation`：同步 `display_break_lines` 新格式约束，禁止 `text` 含 `\n`；③ `attach-script-assets`：`segment_id` 必须用 `segments[i].id` 字段值而非数字索引，路径写回前须磁盘核验；④ `generate-character-images`：写回 `character_refs` 时必须使用生图返回的实际文件名，不得按角色名推断（防止汉字拼写差异导致路径悬空）。
- 2026-03-03：`display_break_lines` 改为字符串数组格式（每项=该步新增文本行，引擎累积拼接渲染）；`text` 字段在有 `display_break_lines` 时统一留空，消除内容重复，约减 40% 脚本文件体积。`_build_step_texts` 兼容旧整数断点格式。
- 2026-03-03：修复最后一段播完后不显示剧终、以及长段不能分步推进的问题：① `_advance()` 在 `next_id is None` 时直接展示"— 终 —"并清空 `current_id`；② `_build_step_texts()` 在无 `display_break_lines` 时按中文句尾标点（`。！？…`）自动拆分为累积步进，每次按空格显示下一句。
- 2026-03-03：修复引擎 segment 导航 Bug：`_start_script` 加载列表型 segments 时改为优先使用 segment 自带 `id` 字段作为字典键（回退数字索引兼容旧脚本），自动补充的 `next` 也指向下一段真实 id，解决具名 id（如 `"s2"`）在 `segments` 中查找为 `None` 导致第一段播完即跳剧终的问题。
- 2026-03-03：明确混元文件接口两项限制：① `enable_deep_read=true` 默认未开通，必须传 `false`；② `context_files` 仅支持 `.txt` 格式不支持 `.md`；同步到 `create-script` skill 与本文档。
- 2026-03-03：调整长篇分批续写提示词策略：默认"自然承接前文"且不强制每批段尾悬念，仅在用户明确要求章节钩子时才添加悬念约束；同步到 `create-script` 与 `orchestrate-script-production` skill。
- 2026-03-03：`generate_text` 新增同会话并发保护（文件锁 + 超时提示），减少并发调用下的历史竞争与上下文丢失问题。
- 2026-03-03：生文链路升级为"会话+文件上下文"模式：`generate_text` 支持 `session_id` 复用历史消息，支持 `context_files -> FilesUploads -> FileIDs` 挂载，缓解长篇续写上下文截断问题。
- 2026-03-03：新增默认参考文章约定：阶段1/2可使用《铁道银河之夜》作风格参考（`theme_tone_only`），并明确禁止复刻原文/设定；同步到 skills 与 README。
- 2026-03-03：补充编排"结果汇总"口径：需显式输出 `review_after_stage2` 与最终 `review_gate`，并同步 README。
- 2026-03-03：同步 README：补充阶段2 `review_gate` 四种状态示例（`pending_user_review|approved|regenerate_stage2|auto_continue`）及分支语义。
- 2026-03-03：将 pygame 添加到 `.mcp/requirements.txt` 并更新 `bootstrap_env.py` 导入检查，统一依赖管理；补充 Windows PowerShell 执行策略问题到常见问题排障。
- 2026-03-03：补充编排模板：阶段2输出 `review_gate` 扩展为 `pending_user_review|auto_continue|approved|regenerate_stage2`，并增加审稿分支状态示例。

### 9.2 长期里程碑

- 2026-03-03：硬约束三项写入 skills：① 阶段2 `novel_draft` 必须采用人物/环境/心理/对话混合叙事，禁止纯对白体；② 生成 `novel_draft` 时必须将 `planning_draft` 全文注入生文 API 上下文；③ 新增"阶段2审稿分支"——阶段1提前询问 `review_after_stage2`，审稿通过后才继续阶段3/4。
- 2026-03-03：调整剧本生成流程：阶段1/2改为"生文 API 先产出传统文本草稿并落盘（`scripts/<script_name>/drafts/`），再由 agent 转换为 `script.json`"，不再要求生文直接产出完整 JSON。
- 2026-03-02：运行时主流程迁移至 `pygame`（`main.py -> engine/pygame_app.py`），支持线性阅读、分步追加、背景渐变/震动、回退与返回菜单。
- 2026-02-28：统一并固化剧本共享数据协议：以 `shared` 作为单一数据源（`planning/style_contract/character_refs/asset_manifest/pipeline_state`），兼容历史 `planning` 迁移。
- 2026-02-28：升级生图稳定性与风格契约：启用双锚点 `style_contract`、分辨率归一化、限流重试与可选 COS 本地参考图上传复用。
- 2026-02-27：重构剧本生产流程为四阶段（澄清规划 → 文本+演出 → 人设图 → 场景资产回写），并完成相关 skills 职责拆分与联动。
- 2026-02-27：生图能力统一为腾讯混元（`hunyuan`），并同步 MCP 配置模板与调用约定。
