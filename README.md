# 剧本阅读器

基于 Python + tkinter 实现的本地剧本阅读器，支持多种文字演出效果，脚本以 JSON 格式编写，开箱即用。

---

## 功能特性

- **主菜单**：自动扫描 `scripts/` 目录，动态展示所有可用游戏
- **逐段叙事**：按空格键或鼠标左键推进剧情
- **剧情分支**：段落可设置多个选项，点击或按数字键进入不同剧情线
- **历史回退**：按 BackSpace 键返回上一段（剧情进行中有效，结局画面除外）
- **文字演出效果**：支持四种内置效果
  - `fadein` — 文字渐显
  - `typewriter` — 打字机逐字输出
  - `shake` — 文字震动（适合惊险场景）
  - `wave` — 逐字弹入波浪效果
- **左侧 Tab 工具栏**：通过 Tab 切换“剧本/操作/帮助”界面
- **背景图层**：段落可配置背景图，支持渐变切换与震动
- **右侧人物栏**：显示当前说话人物与立绘（可由脚本指定）
- **自适应窗口模式**：主菜单默认 `1280x720`；进入阅读后自动向左右扩展侧栏，窗口可自由缩放
- **文字可读性增强**：剧情文字下方自动渲染半透明黑色底板（保留背景可见区域）
- **剧本 Tab 可视化**：可查看当前剧本进度与分支去向映射
- **跳过动画**：按空格键可跳过当前动画，直接显示完整文本
- **返回菜单**：按 ESC 键随时返回主菜单

---

## 环境要求

- Python 3.10+
- tkinter（Python 标准库，通常无需额外安装）

---

## 快速开始

```bash
python main.py
```

## 开发文档

- 开发指南：`docs/DEVELOPMENT.md`
- 约定：Agent 修改代码时会同步维护该文档

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

### 腾讯混元生图接入

本项目生图能力已精简为仅支持腾讯混元。请在 `.vscode/mcp.json` 配置：

```jsonc
"API_PROVIDER": "hunyuan",
"TENCENT_SECRET_ID": "你的腾讯云 SecretId",
"TENCENT_SECRET_KEY": "你的腾讯云 SecretKey",
"TENCENT_TOKEN": "",
"HUNYUAN_REGION": "ap-guangzhou",
"HUNYUAN_ENDPOINT": "aiart.tencentcloudapi.com",
"HUNYUAN_API_ACTION": "TextToImageLite",
"HUNYUAN_RSP_IMG_TYPE": "url"
```

说明：
- `TextToImageLite`：混元极速版（文生图）
- `SubmitTextToImageJob`：混元 3.0 任务接口（可配合图生图）
- 代码会按 `api_action` 或环境变量 `HUNYUAN_API_ACTION` 选择接口。

重启 VS Code 后，可直接在对话中让 Agent 生成图片（保存到 `docs/scenes/`）。

资源目录约定：建议按剧本名分目录保存，使用 `docs/scenes/<剧本名>/`，例如：
- `docs/scenes/迷失之森/scene_forest_night.png`
- `docs/scenes/午夜密室/char_detective_tense.png`

---

## 脚本格式

游戏脚本为 JSON 文件，放置于 `scripts/` 目录下，引擎启动时自动识别。支持两种格式：

### 线性格式（数组）

段落按顺序排列，自动逐段推进，适合无分支的线性叙事。

```json
{
  "title": "游戏标题",
  "description": "在主菜单显示的简介",
  "segments": [
    {
      "text": "段落文字内容，支持 \\n 换行",
      "effect": "fadein",
      "speed": 30
    },
    {
      "text": "下一段文字",
      "effect": "typewriter"
    }
  ]
}
```

### 分支格式（字典）

段落以具名 ID 组织，通过 `choices` 或 `next` 字段控制跳转，适合多结局、多分支故事。

```json
{
  "title": "游戏标题",
  "description": "在主菜单显示的简介",
  "start": "intro",
  "segments": {
    "intro": {
      "text": "故事开头……",
      "effect": "fadein",
      "choices": [
        {"label": "选择A", "next": "branch_a"},
        {"label": "选择B", "next": "branch_b"}
      ]
    },
    "branch_a": {
      "text": "走了A路……",
      "effect": "typewriter",
      "next": "ending"
    },
    "branch_b": {
      "text": "走了B路……",
      "effect": "shake",
      "next": "ending"
    },
    "ending": {
      "text": "故事结束。",
      "effect": "fadein"
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 游戏标题 |
| `description` | string | 主菜单简介 |
| `start` | string | 起始段落 ID（仅分支格式，默认第一个） |
| `segments` | array 或 object | 段落列表或段落字典 |
| `text` | string | 段落文字，`\n` 换行 |
| `effect` | string | 演出效果，默认 `fadein` |
| `speed` | int | 动画速度（毫秒/帧），默认 `30` |
| `next` | string | 下一段落的 ID（分支格式中无选项时使用） |
| `choices` | array | 选项列表，每项含 `label`（文字）和 `next`（跳转 ID） |
| `speaker` | string | 当前段落说话人名称，显示在右侧人物栏 |
| `character_image` | string | 当前段落人物图路径（相对项目根目录或绝对路径） |
| `background` | object | 背景图配置对象（见下方） |

### 背景配置（`background`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `image` | string | 背景图路径（建议放 `docs/scenes/`） |
| `effects` | array[string] | 可选：`fade`、`shake` |
| `fade_ms` | int | 渐变时长（毫秒） |
| `shake_ms` | int | 震动时长（毫秒） |
| `shake_strength` | int | 震动强度（像素） |

### 演出效果一览

| effect | 效果 | 推荐 speed | 适用场景 |
|--------|------|-----------|----------|
| `fadein` | 文字渐显 | 20–35 | 通用叙述 |
| `typewriter` | 打字机逐字 | 50–80 | 对话、独白 |
| `shake` | 震动（红色） | 15–20 | 危险、惊吓 |
| `wave` | 波浪弹入 | 18–25 | 奇幻、神秘 |

---

## 操作说明

| 操作 | 功能 |
|------|------|
| `空格键` / `鼠标左键` | 跳过当前动画 / 下一段（无选项时） |
| `1` ~ `9` | 快速选择对应编号的选项 |
| `BackSpace` | 返回上一段（剧情进行中有效，结局画面不可用） |
| `ESC` | 返回主菜单（任意时刻均有效） |

---

## 项目结构

```
Playwright/
├── main.py               # 入口：窗口初始化与页面切换
├── .claude/skills/       # Copilot Skills
│   ├── create-script/                 # 世界观/人设/剧本文本（纯文本）
│   ├── configure-script-presentation/ # 剧本表现字段配置
│   ├── generate-character-images/     # 人物设定图生成
│   ├── generate-scene-assets/         # 背景图与立绘流程生成
│   ├── attach-script-assets/          # 资源路径回写（background/character）
│   ├── orchestrate-script-production/ # 端到端编排统筹（仅调度子 skill）
│   ├── setup-local-env/               # 本地环境自检与部署
│   └── iterate-skills/                # skills 迭代优化与联动更新
├── engine/               # 引擎模块
│   ├── config.py         # 颜色常量与脚本目录路径
│   ├── utils.py          # 颜色插值等工具函数
│   ├── effects.py        # 四种文字演出效果实现与注册表
│   ├── background_controller.py # 背景图控制（适配/渐变/震动）
│   ├── character_panel.py # 右侧人物栏组件
│   ├── menu.py           # 主菜单界面
│   └── game_frame.py     # 游戏界面（脚本加载、段落展示、交互逻辑）
├── scripts/              # 游戏脚本目录
│   ├── 迷失之森.json      # 线性示例：神秘森林冒险（11段）
│   └── 午夜密室.json      # 分支示例：推理悬疑多结局
│   └── bootstrap_env.py  # 本地环境自检与部署脚本
├── docs/scenes/          # 背景图/人物图等资源
├── .gitignore
└── README.md
```

---

## 示例脚本

**《迷失之森》**（[scripts/迷失之森.json](scripts/迷失之森.json)）— 线性格式

> 夜幕低垂，你独自踏入一片陌生的神秘森林……

包含 11 段线性剧情，涵盖全部四种演出效果，适合快速体验基础功能。

---

**《午夜密室》**（[scripts/午夜密室.json](scripts/午夜密室.json)）— 分支格式

> 深夜十二点，你被邀请前往废弃庄园调查失踪案……

包含多条剧情线路、三种不同结局，对话选项影响故事走向。剧情进行中可按 BackSpace 回退，到达结局后仅可按 ESC 返回主菜单。

---

## 添加新游戏

1. 在 `scripts/` 目录下新建一个 `.json` 文件
2. 按照上方脚本格式编写
3. 重新启动 `main.py`，主菜单中将自动出现新游戏
