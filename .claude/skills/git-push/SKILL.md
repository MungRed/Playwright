---
name: git-push
description: 暂存并提交 Git 改动，支持按主题拆分多次提交以提升提交历史可维护性。关键词：git, commit, 提交, 暂存, add, push, 拆分提交, 分批提交
---

## 功能说明

自动完成 Git 提交流程，支持**单次提交**与**拆分多次提交**。当改动跨多个主题时，优先拆分提交，保证历史清晰、易审查、易回滚。

## 执行步骤

1. 运行 `git status` 查看当前改动，分析变更类型与文件分组（功能、修复、文档、配置等）。
2. **在执行任何操作前，先询问用户以下问题：**
  - **提交模式**：一次提交，还是按主题拆分多次提交（默认推荐拆分）
  - **拆分粒度**：按模块/目录拆分，还是按改动类型拆分（`feat/fix/docs/chore`）
  - **提交信息**：是否有指定提交信息（若无则自动生成）
  - **暂存范围**：暂存全部（`git add -A`）还是仅已追踪文件（`git add -u`）
  - **是否推送**：提交后是否执行 `git push`
  - **推送分支**：如需推送，推送到哪个远程分支（默认 `origin` 当前分支）
3. 根据用户回答执行：
   - **单次提交模式**
     - 按用户选择暂存文件
     - 若用户未提供提交信息，自动生成 Conventional Commits 风格信息
     - 执行 `git commit -m "<提交信息>"`
   - **拆分提交模式**
     - 先输出“拟拆分提交计划”（每组：文件列表、提交类型、提交信息），并让用户确认
     - 按组循环执行：
       1) `git add <该组文件>`（必要时使用 `git add -p`）
       2) `git commit -m "<该组提交信息>"`
       3) 汇报当前组结果，再继续下一组
     - 原则：每个提交只包含一个变更意图，不混入无关改动
   - 若用户选择推送，在全部提交完成后执行一次 `git push <remote> <branch>`
4. 输出最终执行结果（提交数量、提交信息摘要、是否已推送）。

## 提交信息规范

- 使用中文或英文均可，与项目保持一致。
- 格式：`<type>(<scope>): <subject>`，例如 `feat(login): 添加记住密码功能`。
- `subject` 简明扼要，不超过 50 个字符。
- 拆分提交时，每个提交保持单一目的，避免“混合提交”。

### 常用类型

- `feat:` 新增功能
- `fix:` 修复 Bug
- `docs:` 文档变更
- `style:` 代码格式（不影响功能）
- `refactor:` 代码重构
- `test:` 新增或修改测试
- `chore:` 构建流程/工具变更

## 拆分策略（推荐）

- 优先按**改动目的**拆分：`feat` / `fix` / `docs` / `chore`
- 其次按**模块或目录**拆分：如 `engine`、`scripts`、`.claude/skills`
- 重构与功能同时存在时，先提交 `refactor`，再提交 `feat/fix`
- 配置与文档改动尽量独立提交，便于评审与回滚

## 示例

```bash
# 1) 引擎功能改动
git add engine/game_frame.py engine/effects.py
git commit -m "feat(engine): 优化文本渲染与交互体验"

# 2) 环境与脚本改动
git add scripts/bootstrap_env.py .claude/skills/setup-local-env/SKILL.md
git commit -m "chore(setup): 新增本地环境自检与初始化脚本"

# 3) 文档改动
git add README.md
git commit -m "docs(readme): 更新环境初始化与安全配置说明"

# 4) 推送
git push origin master
```
