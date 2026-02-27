# 文字冒险游戏引擎

基于 Python + tkinter 实现的本地文字冒险游戏引擎，支持多种文字演出效果，脚本以 JSON 格式编写，开箱即用。

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
- **进度条**：顶部实时显示当前阅读进度
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
│   └── setup-local-env/  # 本地环境自检与部署 skill
├── engine/               # 引擎模块
│   ├── config.py         # 颜色常量与脚本目录路径
│   ├── utils.py          # 颜色插值等工具函数
│   ├── effects.py        # 四种文字演出效果实现与注册表
│   ├── menu.py           # 主菜单界面
│   └── game_frame.py     # 游戏界面（脚本加载、段落展示、交互逻辑）
├── scripts/              # 游戏脚本目录
│   ├── 迷失之森.json      # 线性示例：神秘森林冒险（11段）
│   └── 午夜密室.json      # 分支示例：推理悬疑多结局
│   └── bootstrap_env.py  # 本地环境自检与部署脚本
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
