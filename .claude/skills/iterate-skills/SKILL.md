---
name: iterate-skills
description: 批量迭代本仓库全部 skills，确保与最新流程一致（文档先行 + 三模块解耦 + 纯 agent 编排）。关键词：skill, 迭代, workflow, agent-first
---

## 目标

对 `.claude/skills/**/SKILL.md` 做一致性更新，保证所有 skill 同时满足：
- 文档先行
- 三模块可独立执行
- 纯 agent 编排（不新增流程脚本）

## 执行步骤

1. 读取 `docs/DEVELOPMENT.md`、`docs/PITFALLS.md`、`.github/copilot-instructions.md`。
2. 扫描全部 skill，标记冲突项：
   - 仍引用已废弃流程命令
   - 仍采用四阶段或耦合描述
   - 未体现文档先行
3. 批量修正并保持文件边界不变。
4. 输出变更摘要：文件列表 + 每个文件1-2条关键改动。

## 强约束

1. 不得引入新的专用 Python 流程脚本要求。
2. 统一使用 `shared` 单一数据源协议。
3. 保持 skill 描述简洁、可执行、可追溯。
