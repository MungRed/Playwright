---
name: setup-local-env
description: 初始化本地运行环境（venv + 依赖 + MCP 配置检查），不依赖项目内 bootstrap 脚本。关键词：环境, venv, 依赖, mcp
---

## 职责

在新机器上完成最小可运行环境搭建。

## 执行步骤

1. 检查关键文件：`main.py`、`.mcp/requirements.txt`、`.vscode/mcp.example.jsonc`。
2. 创建或复用 `.venv`。
3. 安装依赖：`.mcp/requirements.txt`。
4. 校验关键导入：`mcp/httpx/Pillow/pygame`。
5. 检查 MCP 本地配置文件是否从模板创建。

## 输出

- `已完成 / 部分完成 / 失败`
- 可直接复制执行的修复命令
- 关键错误摘要

## 注意事项

- 不覆盖用户已有 `.vscode/mcp.json` 与 `.mcp.json`。
- 环境修复优先增量操作，避免破坏用户本地配置。

