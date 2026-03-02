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
- `scripts/bootstrap_env.py`：本地环境检查与初始化

---

## 4. 运行与开发

### 4.1 启动项目

```bash
pip install pygame
python main.py
```

### 4.2 初始化环境（推荐）

```bash
python scripts/bootstrap_env.py
```

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

### 5.1 线性格式

- `segments` 为数组
- 系统会自动补 `next` 链（当段落无 `next` 时）

### 5.2 常用字段

- `shared`: 剧本流水线共享数据容器（推荐）
- `text`: 段落正文
- `display_break_lines`: 同段分步断点（按原文行号断开）
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
		- 当 `planning_source=user_keywords` 时，建议写入 `user_keywords`（`worldview`/`characters`/`outline`）
	- `shared.style_contract`：双锚点画风约束
		- `background_style_anchor` / `background_negative_anchor`
		- `character_style_anchor` / `character_negative_anchor`
	- `shared.character_refs`：人物设定图路径清单
	- `shared.asset_manifest`：段落资产映射（`segment_id`、`background_image`、`character_image`）
	- `shared.pipeline_state`：阶段进度与统计信息
- 兼容历史脚本：若仅有顶层 `planning`，可读取后迁移到 `shared.planning`。
- 默认约定：用户未指定大纲来源时，`planning_source=ai_auto`。
- 编排执行约定：阶段1（规划）完成后，默认自动连续执行阶段2-4；仅在阶段失败或关键参数缺失时再询问用户意见。
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

- 同一段优先通过 `display_break_lines` 配置分步显示：空格/左键优先追加显示下一步文本。
- 单步动画播放期间再次空格/左键为“跳过当前步动画并直接显示完整步”。
- 当前段最后一步显示完成后，下一次空格/左键才进入下一段。
- 同段后续步骤采用“追加显示”策略，不重复从首字符重播整步动画。
- 动画阶段与静态阶段均使用黑色描边文字渲染，以保持视觉一致性。
- 引擎不自动按句切分；未配置分步字段时默认整段一次显示。

---

## 7. 配置与安全

- 仓库不提交真实 API 配置：`.vscode/mcp.json` 已忽略
- 提交模板：`.vscode/mcp.example.jsonc`
- 新成员拉取后自行填写本地 `API_KEY`
- AI 提供商：仅 `hunyuan`（腾讯混元）
- 生文按腾讯云官方 `ChatCompletions` 调用（Endpoint: `hunyuan.tencentcloudapi.com`，版本 `2023-09-01`）
- 生图按腾讯云官方 `TextToImageLite / SubmitTextToImageJob` 调用
- 生文默认模型由 `HUNYUAN_TEXT_MODEL` 控制，生图接口域名由 `HUNYUAN_ENDPOINT` 控制
- 剧本文本生产约束：阶段1/2（规划与正文）必须通过生文 API 生成，不允许跳过 API 直接离线产出完整文本。
- 文本生成流程约束：不要求生文 API 直接返回完整 JSON；应先生成传统文本草稿，再由本地 agent 转换为 `segments` 结构，减少 token 浪费并提升创作自由度。
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

- 2026-03-02：调整剧本生成流程：阶段1/2改为“生文 API 先产出传统文本草稿并落盘（`scripts/<script_name>/drafts/`），再由 agent 转换为 `script.json`”，不再要求生文直接产出完整 JSON。
- 2026-03-02：主菜单剧本列表改为可滚动，移除“最多显示约 5 个剧本”的可视限制；支持鼠标滚轮与 `↑/↓` 键滚动，并新增滚动条与底部提示文案。
- 2026-03-02：修复运行时“找不到剧本”问题：`engine/pygame_app.py` 读取 `script.json` 改为 `utf-8-sig`，兼容带 BOM 的 UTF-8 文件，避免菜单扫描时被静默跳过。
- 2026-03-02：项目结构迁移为“每个剧本一个目录”：`scripts/<script_name>/script.json + assets/`；引擎菜单改为扫描子目录 `script.json`，并优先按剧本目录解析相对资源路径。
- 2026-03-02：更新 `create-script` 与 `orchestrate-script-production`：剧本生成阶段（规划/正文）强制调用生文 API（`mcp_playwright-im_generate_text`），若调用失败需中断并询问“重试/降级/终止”。
- 2026-03-02：将混元生文默认模型从 `hunyuan-turbos-latest` 切换为 `hunyuan-pro`，同步更新 `.mcp/image_gen_server.py`、`.vscode/mcp.example.jsonc`、`.vscode/mcp.json` 与 README 说明。
- 2026-03-02：`.mcp/image_gen_server.py` 新增混元生文 `generate_text` 工具，接入 `ChatCompletions`（非流式）并复用统一重试策略；同时在 `.vscode/mcp.example.jsonc` 增加 `HUNYUAN_TEXT_ENDPOINT` / `HUNYUAN_TEXT_MODEL`。
- 2026-03-02：补充图生图硬规则：`reference_images` 若为本地路径，必须先上传/复用 COS 获取 `https` URL，再调用 `SubmitTextToImageJob`；禁止直接传本地路径。
- 2026-03-02：修复编排流程问题：阶段1后改为自动执行阶段2-4（仅失败时询问）；并新增 `title` 与文件名一致性校验；剧情立绘改为强制图生图 + 竖向分辨率输出。
- 2026-03-02：更新剧本创作流程：阶段1支持“AI 自动生成 / 用户关键词”两种大纲来源；`shared.planning` 新增 `planning_source`，关键词模式建议写入 `user_keywords`。
- 2026-03-02：将“最近 12 条超限处理规则”同步到 README 的文档维护说明，避免团队仅阅读 README 时遗漏。
- 2026-03-02：新增维护规则：当“最近 12 条”超限时，最旧条目按“先评估长期价值，里程碑归档，否则移除”自动处理。

### 9.2 长期里程碑

- 2026-03-02：运行时主流程迁移至 `pygame`（`main.py -> engine/pygame_app.py`），支持线性阅读、分步追加、背景渐变/震动、回退与返回菜单。
- 2026-02-28：统一并固化剧本共享数据协议：以 `shared` 作为单一数据源（`planning/style_contract/character_refs/asset_manifest/pipeline_state`），兼容历史 `planning` 迁移。
- 2026-02-28：升级生图稳定性与风格契约：启用双锚点 `style_contract`、分辨率归一化、限流重试与可选 COS 本地参考图上传复用。
- 2026-02-27：重构剧本生产流程为四阶段（澄清规划 → 文本+演出 → 人设图 → 场景资产回写），并完成相关 skills 职责拆分与联动。
- 2026-02-27：生图能力统一为腾讯混元（`hunyuan`），并同步 MCP 配置模板与调用约定。
