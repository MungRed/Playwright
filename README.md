# AI 小说/剧本/图片资产流水线

本项目主产品是一个由 agent 编排的 AI 创作流水线：

- 模块1：AI 生成完整小说
- 模块2：AI 根据完整小说生成剧本 JSON
- 模块3：AI 根据剧本内分镜生成图片资产（人设图/背景图/立绘）

`Python + pygame` 剧本阅读器仅作为附带产品，用于预览与验收流水线产出的 `script.json`。

---

## 流水线特性

- **三模块解耦**：小说、剧本、图片资产都可独立运行
- **文档先行**：每个模块执行前先定义输入/输出/验收标准
- **纯 agent 编排**：不新增专用 Python 流程脚本
- **统一协议**：`shared` 作为共享数据单一来源
- **质量门禁**：剧本模块支持结构与 AI 评审门禁

## 流水线入口（推荐）

主入口 skill：`orchestrate-script-production`

也可独立调用：

- 模块1：`generate-novel`
- 模块2：`generate-script`
- 模块3：`generate-scene-assets`

详细契约见：`docs/PIPELINE_MODULES.md`

## 快速开始

### 环境准备

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r .mcp/requirements.txt
```

### 运行流水线（Agent 编排）

在支持 MCP 的 agent 会话中，按三模块执行：

1. 先更新模块文档（输入/输出/验收）
2. 调用 `orchestrate-script-production` 或逐个调用三主模块 skill
3. 产物写入 `scripts/<script_name>/`

### 模块2质量工具（强烈建议）

在 agent 生成完 `script.json` 后，建议立刻执行以下两步：

```bash
# 1) 质量检查（结构、旁白占比、长度、立绘约束）
.venv\Scripts\python.exe tools/check_script_quality.py scripts/盲人侦探/script.json --min-narration-ratio 0.45

# 2) 根据小说自动增强旁白并修复格式（可直接覆盖）
.venv\Scripts\python.exe tools/enrich_script_narration.py scripts/盲人侦探/script.json scripts/盲人侦探/drafts/novel_full.md --target-ratio 0.45 --in-place
```

说明：
- `check_script_quality.py` 只检查，不改文件。
- `enrich_script_narration.py` 会执行“旁白补强 + 超长分句 + id 重排 + asset_manifest 重建”。

### 模块2增强工具（v2）

```bash
# 3) 从完整小说自动切片生成分镜草案（用于模块2前置规划）
.venv\Scripts\python.exe tools/plan_storyboards_from_novel.py scripts/盲人侦探/drafts/novel_full.md --target-count 6 --output scripts/盲人侦探/drafts/storyboard_plan.json

# 4) 自动多轮修复（结构 + 旁白密度），直到通过或达到轮次上限
.venv\Scripts\python.exe tools/auto_refine_script.py scripts/盲人侦探/script.json scripts/盲人侦探/drafts/novel_full.md --min-narration-ratio 0.45 --max-rounds 3 --in-place
```

推荐将模块2固定为以下闭环：

1. 生成初稿
2. 执行本地门禁
3. 执行本地修复工具
4. 调用 `review-script` 做混元复评
5. 若 `delivery_gate=rewrite_needed`，按建议定向改写并重复 2-4，最多 3 轮

---

## 附带产品：剧本阅读器

用于播放流水线产出的剧本 JSON，支持本地预览与演出效果检查。

### 阅读器功能特性

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

### 运行阅读器

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

## 文档与规范

- 模块契约：`docs/PIPELINE_MODULES.md`
- 开发指南：`docs/DEVELOPMENT.md`
- 踩坑记录：`docs/PITFALLS.md`

### 文档维护规则

- 变更记录维护：`docs/DEVELOPMENT.md` 采用“最近 N 条 + 长期里程碑”结构（当前 `N=12`）
- 超过 12 条时：最旧“最近条目”先评估长期价值；有长期价值迁移到“长期里程碑”，否则直接移除

### MCP 配置说明（双轨制）

本项目支持两种 AI 编辑环境，各有独立的 MCP 配置文件：

| 环境 | 配置文件 | 模板文件 | 用途 |
|------|---------|---------|------|
| **VSCode 扩展** | `.vscode/mcp.json` | `.vscode/mcp.example.jsonc` | VSCode 内置的 Copilot/插件 |
| **Claude Code CLI** | `.mcp.json` | `.mcp.example.json` | Claude Code 对话窗口 |

**配置步骤**：

1. **手动初始化**：
   ```bash
   # VSCode 扩展配置
   cp .vscode/mcp.example.jsonc .vscode/mcp.json

   # Claude Code CLI 配置
   cp .mcp.example.json .mcp.json
   ```

2. **填写密钥**：
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

游戏脚本为 JSON 文件，放置于 `scripts/` 目录下，引擎启动时自动识别。
当前统一协议为 `storyboards -> scripts` 两层结构。

```json
{
  "title": "游戏标题",
  "description": "在主菜单显示的简介",
  "storyboards": [
    {
      "id": "sb1",
      "title": "雨中算命",
      "background": { "image": "assets/rain_fortune_stall.png" },
      "scripts": [
        {
          "id": "s1",
          "speaker": "旁白",
          "text": "雨丝斜斜划过青石板路。",
          "character_image": null,
          "effect": "typewriter",
          "speed": 55
        },
        {
          "id": "s2",
          "speaker": "盲眼法医",
          "text": "问什么？",
          "character_image": "assets/char_blind_detective_calm.png",
          "effect": "typewriter",
          "speed": 55
        }
      ],
      "quality_gate": { "target_narration_ratio": 0.4 }
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
| `storyboards` | array | 分镜列表 |
| `storyboards[].id` | string | 分镜唯一标识（如 `sb1`） |
| `storyboards[].title` | string | 分镜标题 |
| `storyboards[].background.image` | string | 背景图路径（建议 `assets/` 下相对路径） |
| `storyboards[].scripts` | array | 分镜内段落 |
| `scripts[].id` | string | 段落唯一标识（如 `s1`） |
| `scripts[].speaker` | string | 说话人，旁白固定为 `旁白` |
| `scripts[].text` | string | 段落正文，建议单条 <= 80 字 |
| `scripts[].character_image` | string/null | 对话段为立绘路径，旁白段应为 `null` |
| `scripts[].effect` | string | 演出效果，默认 `typewriter` |
| `scripts[].speed` | int | 当 `effect=typewriter` 时固定 `55` |
| 质量门禁 | agent | 模块2后建议调用 `review-script` 执行质量门禁 |
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

### 文本生成流程约定（模块1/2）

- 生文 API（`mcp_playwright-im_generate_text`）优先产出传统文本（规划稿、完整小说、剧本文本），而不是直接输出完整 JSON。
- 草稿先落盘到 `scripts/<script_name>/drafts/`，再由 agent 本地转换成 `script.json` 的 `storyboards` 结构。
- 长篇续写建议开启会话复用：为连续调用传入同一个 `session_id`，并在后续轮次使用 `use_session_history=true` 自动注入历史消息。
- 当上下文过长时，建议传 `context_files`（本地路径或 URL）让服务端先走 `FilesUploads` 并将返回 `FileIDs` 挂到 user 消息，避免消息体截断。
- 会话续写默认开启 `carry_forward_file_ids=true`：即使后续轮次未重复传 `context_files`，也会自动继承最近历史中的 `FileIDs`。
- 同一 `session_id` 的多轮调用建议串行发起；服务端已增加会话锁，若并发冲突会等待并在超时后返回明确错误。
- **`enable_deep_read` 注意**：深度阅读功能默认未开通，调用时必须传 `enable_deep_read=false`；传 `true` 会触发 `InvalidParameter` 报错。
- 模块1生成 `novel_full` 时，必须注入 `planning_draft` 内容（建议全文），确保前后设定一致。
- 模块1 `novel_full` 需采用视觉小说叙事混合写法：人物描写、环境描写、心理描写 + 对话；不建议全篇纯对白。
- 默认参考文章为《铁道银河之夜》，仅用于主题氛围与节奏参考，不得复写原文、角色名、专有设定或关键桥段。
- 模块1需提前确认 `review_after_stage2`：
  - `true`：模块2后暂停，先让用户检查剧本，再按反馈“重生成模块2”或“继续后续模块”；
  - `false`：模块2后自动继续模块3。
- 模块2审稿分支状态（`review_gate`）建议统一使用：
  - `pending_user_review`：模块2已完成，等待用户检查；
  - `approved`：用户确认通过，继续模块3；
  - `regenerate_stage2`：用户要求按反馈重生成模块2；
  - `auto_continue`：未启用审稿分支，自动继续模块3。
- 结果汇总建议显式输出 `review_after_stage2` 与最终 `review_gate`，便于自动化消费与人工追踪。
- 推荐草稿文件：
  - `scripts/<script_name>/drafts/planning_draft.md`
  - `scripts/<script_name>/drafts/novel_full.md`

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
│   ├── generate-novel/                # 模块1：生成完整小说
│   ├── generate-script/               # 模块2：根据完整小说生成 script.json
│   ├── configure-script-presentation/ # 剧本表现字段配置
│   ├── generate-scene-assets/         # 模块3：分镜（镜头脚本 + 资产清单）
│   ├── generate-character-images/     # 分镜模块辅助：角色设定图
│   ├── attach-script-assets/          # 分镜模块辅助：资源路径回写
│   ├── orchestrate-script-production/ # 三模块编排统筹（仅调度子 skill）
│   ├── iterate-skills/                # skills 迭代优化与联动更新
│   └── git-push/                      # 暂存提交 Git 改动
├── engine/               # 引擎模块
│   ├── __init__.py
│   └── pygame_app.py     # pygame 主流程（菜单+阅读器）
├── scripts/              # 游戏脚本目录（每个剧本一个文件夹）
│   ├── 银河铁道之夜/
│   │   ├── script.json
│   │   ├── drafts/
│   │   │   ├── planning_draft.md
│   │   │   └── novel_full.md
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
│   └── ...
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

**《盲人侦探》**（[scripts/盲人侦探/script.json](scripts/盲人侦探/script.json)）— 分镜格式

> 雨夜老街中，失明前法医以听觉与嗅觉抽丝剥茧，破解拆迁区连环命案。

当前样例已切换为“旁白 + 对话”混合高密度分镜，适合验证模块2文案质量与模块3资产绑定。

---

## 添加新游戏

1. 在 `scripts/` 目录下新建 `<剧本名>/` 文件夹，并创建 `script.json`、`assets/`、`drafts/`
2. 按照上方脚本格式编写
3. 重新启动 `main.py`，主菜单中将自动出现新游戏

---

## 常见问题排障

- **启动报错 `No module named pygame`**：先创建虚拟环境并安装依赖：`python -m venv .venv`，再执行 `.venv\Scripts\python.exe -m pip install -r .mcp/requirements.txt`。
- **PowerShell 无法激活虚拟环境（禁止运行脚本）**：执行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`，或直接使用 `.venv\Scripts\python.exe main.py` 运行项目。
- **运行脚本后黑屏/无文本**：检查脚本是否包含 `storyboards`，且每个分镜内有非空 `scripts` 列表。
- **背景或立绘不显示**：优先使用相对剧本目录的路径（如 `assets/scene_xxx.png`）。
- **生图调用失败**：检查 `.vscode/mcp.json` 中腾讯云与 COS 相关配置是否完整。
- **环境初始化失败**：检查 Python 版本是否为 3.10+，并重新执行 `.venv\Scripts\python.exe -m pip install -r .mcp/requirements.txt`。
