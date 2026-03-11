---
name: update-readme
description: 同步 README 与当前实现，重点校验是否符合“三阶段解耦 + 纯 agent 编排 + 文档先行”规范。关键词：readme, 文档同步, agent-first
---

## 目标

让 `README.md` 与当前仓库状态完全一致，避免与 `docs/DEVELOPMENT.md` 冲突。

## 必检项

1. 是否明确三阶段流程：小说 -> 剧本 -> 资产。
2. 是否明确“流程由 agent 编排，不新增专用流程脚本”。
3. 是否体现“每阶段先更新文档、再执行、再回写文档”。
4. 运行说明是否与现有目录结构一致。

## 执行步骤

1. 读取 `README.md`、`docs/DEVELOPMENT.md`、`.github/copilot-instructions.md`。
2. 标记冲突段落并做最小修改。
3. 保留原有风格与用户手写章节。
4. 输出修改摘要（章节 + 关键变更）。
