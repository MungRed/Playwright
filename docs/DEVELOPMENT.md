# 开发文档（Development Guide）

## 1. 文档目标

本文件用于记录项目的开发规范、架构约定与关键变更。
任何涉及代码行为、结构、配置或运行方式的改动，都应同步更新本文件。

---

## 2. 项目定位

本项目是基于 `Python + tkinter` 的本地**剧本阅读器**，核心能力：
- 加载 `scripts/*.json` 剧本
- 支持线性与分支阅读
- 支持多种文字演出效果
- 提供左侧 Tab 工具栏（剧本/操作/帮助）
- 支持段落背景图（渐变/震动）与右侧人物栏展示

---

## 3. 目录与职责

- `main.py`：程序入口，窗口初始化与页面切换
- `engine/menu.py`：主菜单（剧本列表展示与进入阅读）
- `engine/game_frame.py`：阅读主界面（状态机、段落推进、交互）
- `engine/sidebar_tabs.py`：左侧 Tab 工具栏组件（模块化 UI）
- `engine/effects.py`：文本演出效果实现与注册
- `engine/background_controller.py`：背景图控制器（加载/适配/渐变/震动）
- `engine/character_panel.py`：右侧人物栏组件（说话人 + 立绘）
- `engine/config.py`：主题色与全局路径配置
- `docs/scenes/*`：背景图与人物图资源
- `scripts/*.json`：剧本数据（线性 / 分支）
- `scripts/bootstrap_env.py`：本地环境检查与初始化

---

## 4. 运行与开发

### 4.1 启动项目

```bash
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

- 生图资源按剧本名分目录保存：`docs/scenes/<script_name>/`。
- MCP 生图工具支持 `script_name` 入参，默认落盘到对应剧本目录。
- 剧本中的 `background.image` / `character_image` 建议引用该子目录相对路径。
- 人物设定图（`char_ref_*`）用于风格与角色一致性参考，不直接绑定到 `character_image`。
- 剧本绑定的人物图应使用剧情立绘（如 `char_<name>_<mood>.png`）。
- 生图服务会在剧本资源目录维护 `docs/scenes/<script_name>/_style_contract.json` 作为风格契约缓存（style/negative 锚点）。

### 5.1 线性格式

- `segments` 为数组
- 系统会自动补 `next` 链（当段落无 `next` 且无 `choices` 时）

### 5.2 分支格式

- `start` 指定起始段落 ID
- `segments` 为对象（键为段落 ID）
- `choices` 中每项必须包含 `label` 与 `next`

### 5.3 常用字段

- `shared`: 剧本流水线共享数据容器（推荐）
- `text`: 段落正文
- `effect`: `fadein | typewriter | shake | wave`
- `speed`: 动画速度（ms/帧）
- `next`: 下一段 ID
- `choices`: 分支选项
- `speaker`: 当前说话人名称（用于右侧人物栏）
- `character_image`: 人物图路径（相对项目根目录或绝对路径）
- `background`: 背景配置对象

### 5.4 共享数据协议（shared）

- 顶层建议使用 `shared` 作为流水线单一共享数据源。
- 推荐由各阶段按最小改动读写：
	- `shared.planning`：阶段1需求摘要、世界观、人设、大纲、剧本形态
	- `shared.style_contract`：双锚点画风约束
		- `background_style_anchor` / `background_negative_anchor`
		- `character_style_anchor` / `character_negative_anchor`
	- `shared.character_refs`：人物设定图路径清单
	- `shared.asset_manifest`：段落资产映射（`segment_id`、`background_image`、`character_image`）
	- `shared.pipeline_state`：阶段进度与统计信息
- 兼容历史脚本：若仅有顶层 `planning`，可读取后迁移到 `shared.planning`。

### 5.5 背景配置（background）

- `image`: 背景图路径（推荐放 `docs/scenes/`）
- `effects`: 背景效果数组，支持 `fade` 与 `shake`
- `fade_ms`: 背景切换渐变时长（毫秒）
- `shake_ms`: 背景震动持续时长（毫秒）
- `shake_strength`: 背景震动强度（像素）

---

## 6. UI 架构约定

### 6.1 阅读页布局

- 左侧：Tab 工具栏（`ReaderSidebarTabs`）
- 中间：阅读主区（固定 `1280x720`，标题、文本画布、选项区、底栏）
- 右侧：人物栏（说话人 + 当前段落立绘）
- 窗口策略：主菜单默认 `1280x720`；进入阅读页后自动扩展左右栏，且窗口允许手动缩放

### 6.4 背景图渲染约定

- 背景图在 `Canvas` 底层渲染，文本特效帧都会先绘制背景再绘制文字。
- 背景图使用 cover 策略适配窗口尺寸（保持比例并居中裁切）。
- 背景切换时可按段落配置执行渐变；惊吓段可配置震动。
- 文本动效仅清理 `text_layer`，不整画布清空，以避免背景快速闪烁。
- 背景图定位使用左上角锚点（`nw`），默认不位移，仅在 `shake` 生效时临时位移，避免非预期像素跳动。

### 6.5 文本可读性约定

- 正文区域在背景图上方增加深色实底板（带外边距，不覆盖整幅背景），避免点状遮罩纹理影响观感。
- 文本起点固定为该底板左上角内边距位置。

### 6.2 进度与分支可视化

- 进度文本由 `GameFrame._update_progress()` 计算
- 通过 `GameFrame._sync_sidebar()` 同步到侧栏
- 剧本 Tab 显示：当前段落、进度、分支去向映射

### 6.3 模块化原则

- 复杂 UI 组件优先拆分到 `engine/` 独立模块
- `game_frame.py` 保持“状态控制 + 业务逻辑”，避免堆叠大量控件细节

---

## 7. 配置与安全

- 仓库不提交真实 API 配置：`.vscode/mcp.json` 已忽略
- 提交模板：`.vscode/mcp.example.jsonc`
- 新成员拉取后自行填写本地 `API_KEY`
- 生图提供商：仅 `hunyuan`（腾讯混元）
- 按腾讯云官方 `TextToImageLite` 调用，依赖 `tencentcloud-sdk-python`
- 生图服务默认支持质量稳定化参数：`scene_type`、`style_anchor`、`negative_anchor`、`enforce_style`、`strict_no_people`、`retry_max`。
- 生图服务默认支持退避重试：`HUNYUAN_RETRY_MAX`、`HUNYUAN_RETRY_BASE_SEC`。
- `TextToImageLite` 会做分辨率归一化以降低失败率：横图→`1280x720`、竖图→`720x1280`、方图→`1024x1024`。
- 提示词策略要求：允许长提示词，推荐按“主体要素 + 构图镜头 + 光照色调 + 材质细节 + 用途约束”分层描述；背景需增加文本可读区留白约束，立绘需增加表情强度与边缘清晰度约束。
- 图生图支持本地参考图自动上传 COS：当启用 `COS_AUTO_UPLOAD_ENABLED=true` 且 `reference_images` 传本地路径时，服务会先按内容哈希 Key 检查对象是否已存在，存在则直接复用 URL，不存在再上传后回填 URL。
- COS 自动上传依赖：`cos-python-sdk-v5`（通过 `.mcp/requirements.txt` 安装）。

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

---

## 9. 最近变更记录

- 2026-02-28：清理并固化 `style_contract` 双锚点结构：移除历史兼容键 `style_anchor`/`negative_anchor`；服务端更新时自动清理旧键，防止字段回流。
- 2026-02-28：将生图风格契约升级为双锚点：`background_*` 与 `character_*` 分离存储，避免背景与角色锚点互相覆盖；并同步 skill 与文档采用长提示词分层写法以提升质量稳定性。
- 2026-02-28：增强 `.mcp/image_gen_server.py` 生图稳定性：新增风格契约持久化（`_style_contract.json`）、`scene_type`/`style_anchor`/`negative_anchor`/`enforce_style`/`strict_no_people` 参数、限流与瞬时失败自动重试（`retry_max` + 退避）、以及 `TextToImageLite` 分辨率归一化；并同步更新流水线 skill 调用约定。
- 2026-02-28：统一剧本流水线共享数据协议：`orchestrate/create-script/configure-script-presentation/generate-character-images/generate-scene-assets/attach-script-assets` 全部改为读取并维护脚本顶层 `shared`（`planning/style_contract/character_refs/asset_manifest/pipeline_state`），并要求兼容历史顶层 `planning` 迁移。
- 2026-02-28：补充“阶段1规划包落盘”约定：剧本 JSON 可选新增顶层 `planning` 字段（需求摘要、世界观、人设、大纲、剧本形态）；并在 `scripts/梦想成为宝可梦大师的我因为下到盗版游戏被迫成为海贼王.json` 实际写入该字段，解决仅在对话中可见而项目内不可追溯的问题。
- 2026-02-28：按 `configure-script-presentation` 规则校准 `scripts/今天也在摸鱼.json`、`scripts/迷失之森.json`、`scripts/午夜密室.json` 的演出层字段（`effect`/`speed`），仅调整表现参数，不改写 `text` 与资源路径字段。
- 2026-02-27：修复 COS 自动上传报错兼容性：`image_gen_server.py` 中 `qcloud_cos` 改为动态导入以避免静态诊断误报；并新增 `COS_BUCKET` 规范化（支持从 COS 完整 URL 解析 bucket 名）。
- 2026-02-27：`.mcp/image_gen_server.py` 新增 COS 自动上传链路：图生图 `reference_images` 支持本地路径，执行“先查 URL（对象存在）再上传”的复用策略；新增配置项（`COS_*`）与 `scripts/upload_to_cos.py` 手动上传脚本。
- 2026-02-27：升级生图质量流程：人物设定图改为“三视图+装饰细节”设定单；剧本应用阶段改为绑定剧情立绘（不再直接使用 `char_ref_*`）；背景图生成增加“无人物”硬约束与同剧本统一风格锚点，并支持更长提示词以提高一致性与细节质量。
- 2026-02-27：修复背景切换在文本动画期间停滞导致的“前后背景半透明叠影”问题：背景渐变与震动改为独立持续刷新；同时将正文底板由点状遮罩改为深色实底，提升可读性与观感一致性。
- 2026-02-27：修复推进剧情时闪烁与立绘偶发消失：切段时选项浮层改为立即隐藏（不执行淡出过渡），并在段落缺少 `character_image` 时保留上一张可用立绘。
- 2026-02-27：为选项浮层增加淡入淡出过渡（含轻微位移动画）；显示与隐藏切换更平滑，隐藏结束后仍保持完全移除。
- 2026-02-27：选项区升级为“按需显示”的半透明浮层：仅在存在 `choices` 时显示并覆盖在画布底部，无选项时完全隐藏。
- 2026-02-27：阅读页选项区改为覆盖在中间画布底部显示（不再占用下方布局高度），修复“选项出现时挤压背景图片”的问题。
- 2026-02-27：重排剧本生产流程为四阶段：①对话澄清并产出人设/大纲/剧本形态；②生成仅文本+演出效果剧本（无图片字段）；③生成人物设定图；④二次阅读剧本后生成背景/立绘并回写；同时在场景资产阶段新增“按场景与情绪聚合复用”的降调用策略以节约 API。
- 2026-02-27：为 `orchestrate-script-production` 补充阶段标准输入/输出字段模板（该版本后续已被四阶段流程模板替代），用于统一跨 skill 交接数据结构。
- 2026-02-27：将阶段 E 抽离为独立 skill `attach-script-assets`（专职回写 `background.image` / `character_image`）；并将 `orchestrate-script-production` 收敛为纯统筹调度，不再直接执行业务回写。
- 2026-02-27：完成历史资源迁移：`docs/scenes` 下已有图片按剧本名移动到子目录（`迷失之森/`、`午夜密室/`），并回写对应脚本中的 `background.image` 与 `character_image` 路径。
- 2026-02-27：生图落盘改为按剧本名分目录（`docs/scenes/<script_name>/`）；`.mcp/image_gen_server.py` 新增 `script_name` 参数并默认隔离资源目录。
- 2026-02-27：为 `generate-scene-assets` 新增“文生图 / 图生图”标准参数模板；并同步 `.vscode/mcp.json` 支持 `HUNYUAN_API_ACTION`、`HUNYUAN_JOB_TIMEOUT_SEC`、`HUNYUAN_JOB_POLL_SEC`。
- 2026-02-27：曾将编排 skill `orchestrate-script-production` 调整为五阶段流程（该版本后续已被“四阶段流程重排”替代）；`.mcp/image_gen_server.py` 保持按 `api_action` 选择腾讯混元 `TextToImageLite` 或 `SubmitTextToImageJob`（含 `QueryTextToImageJob` 轮询）。
- 2026-02-27：重构 skills 流程：`create-script` 聚焦纯文本（世界观/人设/剧情）；新增 `generate-character-images`（人物设定图）、`configure-script-presentation`（演出字段配置）、`generate-scene-assets`（背景图/立绘流程，图生图使用混元3.0，文生图使用混元极速版）；并同步更新 `iterate-skills` 触发映射。
- 2026-02-27：按 `iterate-skills` 规则完成项目驱动联动更新：`create-script` 已同步当前剧本字段（`speaker`、`character_image`、`background`），`setup-local-env` 完成执行规则与输出精简优化。
- 2026-02-27：更新 `.claude/skills/iterate-skills/SKILL.md`：除准确性与 token 优化外，新增“按 `docs/DEVELOPMENT.md` 进行项目驱动的 skill 联动迭代”规则（剧本变更联动 `create-script`，环境变更联动 `setup-local-env`）。
- 2026-02-27：优化窗口几何行为：首次启动窗口居中显示，主菜单/阅读页切换尺寸时保持窗口中心点不变；并优化背景层重绘策略，减少推进剧情时的闪烁。
- 2026-02-27：窗口改为可变大小，主菜单恢复 1280x720，进入阅读页后自动向左右扩展；新增正文半透明黑底并将文本起点对齐到底板左上角内边距；修复背景图偶发像素跳动。
- 2026-02-27：重构阅读页：新增 `background_controller.py` 与 `character_panel.py`，将中间阅读区固定为 1280x720，左右栏向外扩展，并通过分层渲染修复背景图快速闪烁问题。
- 2026-02-27：阅读页新增背景图系统（窗口自适配 + 渐变/震动效果），并新增右侧人物栏（说话人 + 立绘）；同步扩展脚本字段 `speaker`、`character_image`、`background`。
- 2026-02-27：删除其他生图 provider 逻辑，MCP 生图服务精简为仅支持腾讯混元；并将 `.vscode/mcp.json` 同步为模板内容。
- 2026-02-27：根据腾讯混元官方文档重构 `hunyuan` 调用逻辑，改为腾讯云标准鉴权（SecretId/SecretKey + Region + Endpoint）。
- 2026-02-27：新增腾讯混元生图接入（`hunyuan` provider），支持通过 `.vscode/mcp.json` 配置网关与模型后在对话中生成图片。
- 2026-02-27：修复分支剧本在首个选项处报错 `NameError: BG_CARD` 的问题（恢复 `game_frame.py` 所需颜色常量导入）。
- 2026-02-27：项目定位由“文字冒险游戏”调整为“剧本阅读器”。
- 2026-02-27：阅读页改为左侧工具栏，并新增“查看当前进度”。
- 2026-02-27：移除主菜单背景图逻辑，界面简化。
- 2026-02-27：左侧工具栏升级为 Tab 模式，新增“剧本/操作/帮助”，并在剧本 Tab 中可视化展示当前进度与分支映射。
