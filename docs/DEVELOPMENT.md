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

---

## 3. 目录与职责

- `main.py`：程序入口，窗口初始化与页面切换
- `engine/menu.py`：主菜单（剧本列表展示与进入阅读）
- `engine/game_frame.py`：阅读主界面（状态机、段落推进、交互）
- `engine/sidebar_tabs.py`：左侧 Tab 工具栏组件（模块化 UI）
- `engine/effects.py`：文本演出效果实现与注册
- `engine/config.py`：主题色与全局路径配置
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

### 5.1 线性格式

- `segments` 为数组
- 系统会自动补 `next` 链（当段落无 `next` 且无 `choices` 时）

### 5.2 分支格式

- `start` 指定起始段落 ID
- `segments` 为对象（键为段落 ID）
- `choices` 中每项必须包含 `label` 与 `next`

### 5.3 常用字段

- `text`: 段落正文
- `effect`: `fadein | typewriter | shake | wave`
- `speed`: 动画速度（ms/帧）
- `next`: 下一段 ID
- `choices`: 分支选项

---

## 6. UI 架构约定

### 6.1 阅读页布局

- 左侧：Tab 工具栏（`ReaderSidebarTabs`）
- 右侧：阅读主区（标题、文本画布、选项区、底栏）

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

---

## 8. 变更维护规则（必须）

当发生以下任一变更时，必须更新本文件：
- 新增/删除模块文件
- 调整主流程或交互行为
- 修改配置文件名、路径、环境初始化方式
- 变更剧本 JSON 约定或字段语义

更新要求：
- 只更新受影响章节，保持最小改动
- 术语与命名必须与代码一致
- 不写泛化描述，写清“改了什么、影响哪里”

---

## 9. 最近变更记录

- 2026-02-27：删除其他生图 provider 逻辑，MCP 生图服务精简为仅支持腾讯混元；并将 `.vscode/mcp.json` 同步为模板内容。
- 2026-02-27：根据腾讯混元官方文档重构 `hunyuan` 调用逻辑，改为腾讯云标准鉴权（SecretId/SecretKey + Region + Endpoint）。
- 2026-02-27：新增腾讯混元生图接入（`hunyuan` provider），支持通过 `.vscode/mcp.json` 配置网关与模型后在对话中生成图片。
- 2026-02-27：修复分支剧本在首个选项处报错 `NameError: BG_CARD` 的问题（恢复 `game_frame.py` 所需颜色常量导入）。
- 2026-02-27：项目定位由“文字冒险游戏”调整为“剧本阅读器”。
- 2026-02-27：阅读页改为左侧工具栏，并新增“查看当前进度”。
- 2026-02-27：移除主菜单背景图逻辑，界面简化。
- 2026-02-27：左侧工具栏升级为 Tab 模式，新增“剧本/操作/帮助”，并在剧本 Tab 中可视化展示当前进度与分支映射。
