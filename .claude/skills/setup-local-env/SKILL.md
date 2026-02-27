---
name: setup-local-env
description: 自动检查并部署本地环境配置，确保项目在新机器上可直接运行。关键词：环境, 环境配置, 初始化, setup, bootstrap, venv, 依赖, mcp, 本地部署
---

## 功能说明

用于在用户拉取仓库后，自动完成本地环境初始化与自检，尽可能把“能跑起来”所需步骤一次性执行完。

本 skill 负责：
- 检查 Python 版本与解释器可用性
- 创建或复用虚拟环境 `.venv`
- 安装基础依赖（优先 `.mcp/requirements.txt`）
- 校验关键目录与关键模块导入是否成功
- 给出明确的结果摘要与下一步操作

## 执行步骤

1. 读取项目根目录并确认关键文件是否存在：
   - `main.py`
   - `.mcp/requirements.txt`
   - `.vscode/mcp.example.jsonc`

2. 运行一键脚本：
   - Windows / PowerShell：`python scripts/bootstrap_env.py`
   - 如当前 `python` 不可用，优先提示用户安装 Python 3.10+ 并重新执行。

3. 脚本完成后，汇总以下状态并反馈给用户：
   - Python 版本是否满足
   - `.venv` 是否已创建或已复用
   - 依赖安装是否成功
   - `mcp/httpx/Pillow/tkinter` 导入检查结果
   - `docs/scenes` 是否可用
   - `.vscode/mcp.json` 是否已从模板生成

4. 若失败，按最小阻塞原则处理：
   - 依赖安装失败：输出失败包名与重试命令
   - Python 版本不满足：提示安装目标版本（3.10+）
   - MCP 配置缺失：提示可自动生成默认配置（需用户确认）

## 输出规范

- 先给简短结论：`已完成 / 部分完成 / 失败`
- 再给可执行命令（复制即可运行）
- 不输出冗长日志，只保留关键错误摘要

## 注意事项

- 仓库中只提交 `.vscode/mcp.example.jsonc`，不要提交真实 `.vscode/mcp.json`。
- 不要覆盖用户已有 `.vscode/mcp.json`；仅在缺失时从模板创建。
- 环境修复应优先“增量变更”，避免破坏用户已有配置。
- 如果用户明确要求“只检查不改动”，则运行脚本的只读模式：
  - `python scripts/bootstrap_env.py --check-only`

## 常用命令

```bash
# 标准模式：检查 + 自动修复
python scripts/bootstrap_env.py

# 只检查，不做改动
python scripts/bootstrap_env.py --check-only
```

