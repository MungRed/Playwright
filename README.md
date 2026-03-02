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

---

## 快速开始

```bash
pip install pygame
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

### API 配置安全说明（Public 仓库）

- 仓库仅提供模板文件：`.vscode/mcp.example.jsonc`
- 本地实际配置文件：`.vscode/mcp.json`（已在 `.gitignore` 中忽略，不会提交）
- 首次使用可直接运行 `python scripts/bootstrap_env.py`，会自动从模板生成本地配置
- 然后在 `.vscode/mcp.json` 中填写你自己的 `API_KEY`

### 腾讯混元接入（生文 + 生图）

本项目 AI 能力统一使用腾讯混元（生文 + 生图）。请在 `.vscode/mcp.json` 配置：

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
      "text": "段落文字内容，支持 \\n 换行",
      "effect": "typewriter",
      "speed": 55
    },
    {
      "text": "下一段文字",
      "effect": "typewriter"
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
| `text` | string | 段落文字，`\n` 换行 |
| `display_break_lines` | array[int] | 可选：同段分步断点（按原文行号断开，避免重复文本） |
| `effect` | string | 演出效果，默认 `typewriter` |
| `speed` | int | 动画速度（毫秒/帧），`typewriter` 固定 `55` |
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
    "updated_at": "2026-02-28"
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
│   ├── create-script/                 # 世界观/人设/剧本文本（纯文本）
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
│   ├── 迷失之森/
│   │   ├── script.json
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

## 添加新游戏

1. 在 `scripts/` 目录下新建 `<剧本名>/` 文件夹，并创建 `script.json` 与 `assets/`
2. 按照上方脚本格式编写
3. 重新启动 `main.py`，主菜单中将自动出现新游戏

---

## 常见问题排障

- 启动报错 `No module named pygame`：先执行 `pip install pygame`，再运行 `python main.py`。
- 运行脚本后黑屏/无文本：检查脚本是否包含 `segments` 数组与 `text` 字段。
- 背景或立绘不显示：优先使用相对剧本目录的路径（如 `assets/scene_xxx.png`）。
- 生图调用失败：检查 `.vscode/mcp.json` 中腾讯云与 COS 相关配置是否完整。
- 环境初始化失败：运行 `python scripts/bootstrap_env.py --check-only` 查看失败项，再按提示修复。
