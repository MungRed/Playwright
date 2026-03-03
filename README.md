# 剧本阅读器

基于 Python + pygame 实现的本地剧本阅读器，支持多种文字演出效果，脚本以 JSON 格式编写，开箱即用。

---

## 功能特性

- **主菜单**：自动扫描 `scripts/` 目录，动态展示所有可用游戏
- **逐段叙事**：按空格键或鼠标左键推进剧情
- **段内分步追加**：可通过段落配置控制同段文本的分步显示与追加
- **历史回退**：按 BackSpace 键返回上一段（剧情进行中有效，结局画面除外）
- **文字演出效果**：支持两种内置效果
  - `typewriter` — 打字机逐字输出
  - `shake` — 文字震动（适合惊险场景）
- **左侧进度栏**：显示线性进度与当前段落编号
- **背景图层**：段落可配置背景图，支持渐变切换与震动
- **右侧人物栏**：显示人物立绘与操作提示（可由脚本指定）
- **自适应窗口模式**：主菜单默认 `1280x720`；进入阅读后自动向左右扩展侧栏，窗口可自由缩放
- **文字可读性增强**：剧情文字采用黑色描边渲染，保留完整背景画面
- **跳过动画**：按空格键可跳过当前动画，直接显示完整文本
- **返回菜单**：按 ESC 键随时返回主菜单

---

## 环境要求

- Python 3.10+
- pygame

### 版本约束（建议）

- Python：`>=3.10`（推荐 `3.10 ~ 3.12`）
- 运行时：`pygame`（最新稳定版）
- MCP/生图相关依赖（来自 `.mcp/requirements.txt`）：
  - `mcp>=1.0.0`
  - `httpx>=0.27.0`
  - `Pillow>=10.0.0`
  - `tencentcloud-sdk-python>=3.0.1200`
  - `cos-python-sdk-v5>=1.9.37`
  - `pygame>=2.5.0`

---

## 快速开始

### 初始化环境（推荐）

```bash
python scripts/bootstrap_env.py
.venv\Scripts\python.exe main.py
```

### 直接运行（需手动安装依赖）

```bash
pip install pygame httpx Pillow
python main.py
```

---

## 迁移说明（pygame-only）

- 当前主流程已统一为 `pygame`，入口为 `main.py -> engine/pygame_app.py`。
- 旧版 `tkinter` 阅读器模块已移除，不再作为运行路径。
- 主菜单窗口固定 `1280x720`；进入阅读后扩展为“左栏 + 中间阅读区 + 右栏”。
- Windows 下菜单与阅读页切换时会尽量保持窗口中心位置。

## 开发文档

- 开发指南：`docs/DEVELOPMENT.md`
- 约定：Agent 修改代码时会同步维护该文档

### 文档维护规则

- 变更记录维护：`docs/DEVELOPMENT.md` 采用“最近 N 条 + 长期里程碑”结构（当前 `N=12`）
- 超过 12 条时：最旧“最近条目”先评估长期价值；有长期价值迁移到“长期里程碑”，否则直接移除

### 本地环境自检与部署（推荐）

新用户拉取仓库后，建议先执行：

```bash
python scripts/bootstrap_env.py
```

仅检查不改动：

```bash
python scripts/bootstrap_env.py --check-only
```

### MCP 配置说明（双轨制）

本项目支持两种 AI 编辑环境，各有独立的 MCP 配置文件：

| 环境 | 配置文件 | 模板文件 | 用途 |
|------|---------|---------|------|
| **VSCode 扩展** | `.vscode/mcp.json` | `.vscode/mcp.example.jsonc` | VSCode 内置的 Copilot/插件 |
| **Claude Code CLI** | `.mcp.json` | `.mcp.example.json` | Claude Code 对话窗口 |

**配置步骤**：

1. **自动初始化（推荐）**：
   ```bash
   python scripts/bootstrap_env.py
   ```
   此脚本会自动从模板生成两个配置文件。

2. **手动初始化**：
   ```bash
   # VSCode 扩展配置
   cp .vscode/mcp.example.jsonc .vscode/mcp.json

   # Claude Code CLI 配置
   cp .mcp.example.json .mcp.json
   ```

3. **填写密钥**：
   - 编辑 `.vscode/mcp.json`（VSCode 扩展用）
   - 编辑 `.mcp.json`（Claude Code CLI 用）
   - 两个文件都需要填写相同的腾讯云密钥

**安全说明**：
- 两个配置文件均已在 `.gitignore` 中忽略，不会提交到版本库
- 模板文件不包含真实密钥，可以安全提交

### 腾讯混元接入（生文 + 生图）

本项目 AI 能力统一使用腾讯混元（生文 + 生图）。配置示例：

```jsonc
"API_PROVIDER": "hunyuan",
"TENCENT_SECRET_ID": "你的腾讯云 SecretId",
"TENCENT_SECRET_KEY": "你的腾讯云 SecretKey",
"TENCENT_TOKEN": "",
"HUNYUAN_REGION": "ap-guangzhou",
"HUNYUAN_TEXT_ENDPOINT": "hunyuan.tencentcloudapi.com",
"HUNYUAN_TEXT_MODEL": "hunyuan-pro",
"HUNYUAN_ENDPOINT": "aiart.tencentcloudapi.com",
"HUNYUAN_API_ACTION": "TextToImageLite",
"HUNYUAN_RSP_IMG_TYPE": "url",
"HUNYUAN_RETRY_MAX": "3",
"HUNYUAN_RETRY_BASE_SEC": "1.5",
"COS_AUTO_UPLOAD_ENABLED": "false",
"COS_REGION": "ap-guangzhou",
"COS_BUCKET": "",
"COS_KEY_PREFIX": "refs"
```

说明：
- 生文接口：`ChatCompletions`（`hunyuan.tencentcloudapi.com`，版本 `2023-09-01`，默认模型 `hunyuan-pro`）。
- `TextToImageLite`：混元极速版（文生图）
- `SubmitTextToImageJob`：混元 3.0 任务接口（可配合图生图）
- 代码会按 `api_action` 或环境变量 `HUNYUAN_API_ACTION` 选择接口。
- 默认支持限流/瞬时失败自动重试：`HUNYUAN_RETRY_MAX` + `HUNYUAN_RETRY_BASE_SEC`。
- `TextToImageLite` 默认会进行分辨率归一化（横图 `1280x720`、竖图 `720x1280`、方图 `1024x1024`）以降低失败率。
- 当 `COS_AUTO_UPLOAD_ENABLED=true` 时，`reference_images` 支持本地路径：服务会先尝试按哈希 Key 复用 COS 对象 URL，若不存在再上传。
- 同一剧本目录会维护 `_style_contract.json`，用于持续复用 `style_anchor/negative_anchor`，减少风格漂移。
- `_style_contract.json` 采用双锚点：
  - `background_style_anchor` / `background_negative_anchor`
  - `character_style_anchor` / `character_negative_anchor`
  这样可避免背景与角色互相覆盖风格参数。

提示词建议：
- 背景图使用长提示词，至少包含：主体要素、镜头构图、光照色调、材质细节、文本可读区留白。
- 角色图使用长提示词，至少包含：角色识别特征、情绪强度、构图范围、服装延续点、线稿/边缘清晰度约束。

### COS 参考图上传脚本（可选）

用于手动上传本地参考图并输出 URL（同样先查存在再上传）：

```bash
python scripts/upload_to_cos.py scripts/今天也在摸鱼/assets/jtr_char_ref_你_sheet_v2.png --script-name 今天也在摸鱼
```

常用参数：
- `--bucket` / `COS_BUCKET`
- `--region` / `COS_REGION`
- `--signed`（生成临时签名 URL，适合私有读桶）

重启 VS Code 后，可直接在对话中让 Agent 生成图片（保存到 `scripts/<剧本名>/assets/`）。

资源目录约定：每个剧本一个目录，结构如下：
- `scripts/<剧本名>/script.json`
- `scripts/<剧本名>/assets/scene_forest_night.png`
- `scripts/<剧本名>/assets/char_detective_tense.png`

---

## 脚本格式

游戏脚本为 JSON 文件，放置于 `scripts/` 目录下，引擎启动时自动识别。仅支持线性格式：

### 线性格式（数组）

段落按顺序排列，自动逐段推进，适合无分支的线性叙事。

```json
{
  "title": "游戏标题",
  "description": "在主菜单显示的简介",
  "segments": [
    {
      "id": "s1",
      "text": "",
      "display_break_lines": [
        "第一行文字，空格后追加下一行。",
        "第二行文字，再次空格进入下一段。"
      ],
      "effect": "typewriter",
      "speed": 55,
      "next": "s2"
    },
    {
      "id": "s2",
      "text": "单句段落直接写在 text 里（无需分步时）。",
      "effect": "typewriter",
      "speed": 55
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 游戏标题 |
| `description` | string | 主菜单简介 |
| `shared` | object | 流水线共享数据（规划、人设图、资产清单、阶段状态） |
| `segments` | array | 段落列表 |
| `id` | string | 段落唯一标识（如 `"s1"`），引擎用于段落导航 |
| `text` | string | 段落正文。有 `display_break_lines` 时留空 `""`（引擎不读），且不含 `\n` |
| `display_break_lines` | array[string] | 可选：同段分步文本数组，每项为该步新增的一行文本；引擎按步累积拼接渲染。使用此字段时 `text` 留空 |
| `effect` | string | 可选演出效果（常用 `typewriter`/`shake`）；未配置时由引擎按默认行为处理 |
| `speed` | int | 可选动画速度（毫秒/帧）；当 `effect=typewriter` 时固定 `55` |
| 质量门禁 | command | 阶段2后建议运行：`python scripts/quality_audit.py scripts/<script>/script.json --check` |
| `next` | string | 下一段落的 ID（可选，未提供时自动顺序推进） |
| `speaker` | string | 可选：说话人元数据（当前 UI 不单独显示姓名） |
| `character_image` | string | 当前段落人物图路径（相对项目根目录或绝对路径） |
| `background` | object | 背景图配置对象（见下方） |

### 共享数据（`shared`，推荐）

```json
"shared": {
  "planning": {
    "requirements_summary": "...",
    "script_form": "visual_novel",
    "planning_source": "ai_auto",
    "worldview": "...",
    "characters": [{ "name": "林澈", "profile": "..." }],
    "outline": [{ "chapter": 1, "summary": "..." }],
    "user_keywords": {
      "worldview": ["废土", "高塔城"],
      "characters": ["失忆女主", "机械师导师"],
      "outline": ["试炼", "背叛", "真相反转"]
    }
  },
  "style_contract": {
    "background_style_anchor": "anime visual novel background, clean lineart",
    "background_negative_anchor": "低质量, 模糊, 水印, 文本, 人物",
    "character_style_anchor": "anime visual novel character illustration, clean lineart",
    "character_negative_anchor": "低质量, 模糊, 水印, 文本, 畸形"
  },
  "character_refs": [
    { "name": "林澈", "image": "assets/char_ref_林澈_v1.png" }
  ],
  "asset_manifest": [
    {
      "segment_id": "s1",
      "background_image": "assets/scene_s1.png",
      "character_image": "assets/char_林澈_calm.png"
    }
  ],
  "pipeline_state": {
    "stage": "4",
    "updated_at": "2026-02-28",
    "review_after_stage2": true,
    "review_gate": "pending_user_review"
  }
}
```

说明：历史脚本若使用顶层 `planning` 仍可兼容读取，建议逐步迁移到 `shared.planning`。

大纲来源约定：
- `planning_source=ai_auto`：由 AI 自动生成世界观/人设/大纲（默认模式）。
- `planning_source=user_keywords`：用户先提供关键词（世界观/人物/大纲），AI 在关键词约束下扩展为完整规划。

### 背景配置（`background`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `image` | string | 背景图路径（建议放 `assets/`，相对 `script.json`） |
| `effects` | array[string] | 可选：`fade`、`shake` |
| `fade_ms` | int | 渐变时长（毫秒） |
| `shake_ms` | int | 震动时长（毫秒） |
| `shake_strength` | int | 震动强度（像素） |

### 文本生成流程约定（阶段1/2）

- 生文 API（`mcp_playwright-im_generate_text`）优先产出**传统文本草稿**（小说/对白体），而不是直接输出完整 JSON。
- 草稿先落盘到 `scripts/<script_name>/drafts/`，再由 agent 本地转换成 `script.json` 的 `segments` 结构。
- 长篇续写建议开启会话复用：为连续调用传入同一个 `session_id`，并在后续轮次使用 `use_session_history=true` 自动注入历史消息。
- 当上下文过长时，建议传 `context_files`（本地路径或 URL）让服务端先走 `FilesUploads` 并将返回 `FileIDs` 挂到 user 消息，避免消息体截断。
- 会话续写默认开启 `carry_forward_file_ids=true`：即使后续轮次未重复传 `context_files`，也会自动继承最近历史中的 `FileIDs`。
- 同一 `session_id` 的多轮调用建议串行发起；服务端已增加会话锁，若并发冲突会等待并在超时后返回明确错误。
- **`enable_deep_read` 注意**：深度阅读功能默认未开通，调用时必须传 `enable_deep_read=false`；传 `true` 会触发 `InvalidParameter` 报错。
- 阶段2生成 `novel_draft` 时，必须注入阶段1 `planning_draft` 内容（建议全文），确保前后设定一致。
- 阶段2 `novel_draft` 需采用视觉小说叙事混合写法：人物描写、环境描写、心理描写 + 对话；不建议全篇纯对白。
- 默认参考文章为《铁道银河之夜》，仅用于主题氛围与节奏参考，不得复写原文、角色名、专有设定或关键桥段。
- 阶段1需提前确认 `review_after_stage2`：
  - `true`：阶段2后暂停，先让用户检查剧本，再按反馈“重生成阶段2”或“继续后续阶段”；
  - `false`：阶段2后自动继续阶段3/4。
- 阶段2审稿分支状态（`review_gate`）建议统一使用：
  - `pending_user_review`：阶段2已完成，等待用户检查；
  - `approved`：用户确认通过，继续阶段3/4；
  - `regenerate_stage2`：用户要求按反馈重生成阶段2；
  - `auto_continue`：未启用审稿分支，自动继续阶段3/4。
- 结果汇总建议显式输出 `review_after_stage2` 与最终 `review_gate`，便于自动化消费与人工追踪。
- 推荐草稿文件：
  - `scripts/<script_name>/drafts/planning_draft.md`
  - `scripts/<script_name>/drafts/novel_draft.md`

### 演出效果一览

| effect | 效果 | 推荐 speed | 适用场景 |
|--------|------|-----------|----------|
| `typewriter` | 打字机逐字 | 55（固定） | 通用文本 |
| `shake` | 震动（红色） | 15–20 | 危险、惊吓 |

---

## 操作说明

| 操作 | 功能 |
|------|------|
| `空格键` / `鼠标左键` | 跳过当前步动画 / 同段按配置追加 / 下一段 |
| `BackSpace` | 返回上一段（剧情进行中有效，结局画面不可用） |
| `ESC` | 返回主菜单（任意时刻均有效） |

---

## 项目结构

```
Playwright/
├── main.py               # 入口：pygame 应用启动
├── .claude/skills/       # Copilot Skills
│   ├── create-script/                 # 世界观/人设/剧本文本（传统草稿->JSON）
│   ├── configure-script-presentation/ # 剧本表现字段配置
│   ├── generate-character-images/     # 人物设定图生成
│   ├── generate-scene-assets/         # 背景图与立绘流程生成
│   ├── attach-script-assets/          # 资源路径回写（background/character）
│   ├── orchestrate-script-production/ # 端到端编排统筹（仅调度子 skill）
│   ├── setup-local-env/               # 本地环境自检与部署
│   ├── iterate-skills/                # skills 迭代优化与联动更新
│   ├── update-readme/                 # 自动同步更新 README
│   └── git-push/                      # 暂存提交 Git 改动
├── engine/               # 引擎模块
│   ├── __init__.py
│   └── pygame_app.py     # pygame 主流程（菜单+阅读器）
├── scripts/              # 游戏脚本目录（每个剧本一个文件夹）
│   ├── 银河铁道之夜/
│   │   ├── script.json
│   │   ├── drafts/
│   │   │   ├── planning_draft.md
│   │   │   └── novel_draft.md
│   │   └── assets/
│   ├── 迷失之森/
│   │   ├── script.json
│   │   ├── drafts/
│   │   └── assets/
│   ├── 午夜密室/
│   │   ├── script.json
│   │   └── assets/
│   ├── 今天也在摸鱼/
│   │   ├── script.json
│   │   └── assets/
│   ├── bootstrap_env.py  # 本地环境自检与部署脚本
│   └── upload_to_cos.py  # COS 参考图上传脚本
├── .gitignore
└── README.md
```

---

## 示例脚本

**《迷失之森》**（[scripts/迷失之森/script.json](scripts/迷失之森/script.json)）— 线性格式

> 夜幕低垂，你独自踏入一片陌生的神秘森林……

包含 11 段线性剧情，涵盖内置演出效果，适合快速体验基础功能。

---

**《午夜密室》**（[scripts/午夜密室/script.json](scripts/午夜密室/script.json)）— 线性格式

> 深夜十二点，你被邀请前往废弃庄园调查失踪案……

包含连续推理剧情与多段场景切换。剧情进行中可按 BackSpace 回退，到达结局后仅可按 ESC 返回主菜单。

---

**《银河铁道之夜》**（[scripts/银河铁道之夜/script.json](scripts/银河铁道之夜/script.json)）— 线性格式

> 改编自宫泽贤治《银河铁道之夜》，以乔瓦尼的视角踏上银河列车，在星光与离别中探寻生命与幸福的意义。

包含 31 段完整旅程，涵盖段内分步推进（`display_break_lines`）、背景图、人物立绘与演出效果，适合体验完整生产流水线产物。

---

## 添加新游戏

1. 在 `scripts/` 目录下新建 `<剧本名>/` 文件夹，并创建 `script.json`、`assets/`、`drafts/`
2. 按照上方脚本格式编写
3. 重新启动 `main.py`，主菜单中将自动出现新游戏

---

## 常见问题排障

- **启动报错 `No module named pygame`**：运行 `python scripts/bootstrap_env.py` 自动创建虚拟环境并安装依赖，或手动执行 `pip install pygame`。
- **PowerShell 无法激活虚拟环境（禁止运行脚本）**：执行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`，或直接使用 `.venv\Scripts\python.exe main.py` 运行项目。
- **运行脚本后黑屏/无文本**：检查脚本是否包含 `segments` 数组，每段须有 `text` 或 `display_break_lines` 字段（两者至少有一个非空）。
- **背景或立绘不显示**：优先使用相对剧本目录的路径（如 `assets/scene_xxx.png`）。
- **生图调用失败**：检查 `.vscode/mcp.json` 中腾讯云与 COS 相关配置是否完整。
- **环境初始化失败**：运行 `python scripts/bootstrap_env.py --check-only` 查看失败项，再按提示修复。
