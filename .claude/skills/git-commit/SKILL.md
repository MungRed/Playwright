---
name: git-commit
description: 暂存所有更改并提交到 Git 仓库。当用户需要提交代码、git commit、暂存文件、写提交信息时使用此 skill。关键词：git, commit, 提交, 暂存, add, push
---

## 功能说明

自动完成 Git 提交的完整流程：检查状态  暂存文件  生成提交信息  提交。

## 执行步骤

1. 运行 `git status` 查看当前改动，分析变更类型
2. 运行 `git add -A` 暂存所有文件
3. 根据改动内容，自动生成符合 Conventional Commits 规范的提交信息：
   - `feat:` 新增功能
   - `fix:` 修复 Bug
   - `docs:` 文档变更
   - `style:` 代码格式（不影响功能）
   - `refactor:` 代码重构
   - `test:` 新增或修改测试
   - `chore:` 构建流程/工具变更
4. 运行 `git commit -m "<生成的提交信息>"`
5. 输出提交结果

## 提交信息规范

- 使用中文或英文均可，与项目保持一致
- 格式：`<type>(<scope>): <subject>`，例如 `feat(login): 添加记住密码功能`
- subject 简明扼要，不超过 50 个字符
- 如涉及多个改动，使用最主要的类型，并在 body 中补充说明

## 示例

```
feat(auth): 添加用户登录功能

- 新增登录页面组件
- 实现 JWT token 验证
- 添加登录状态持久化
```
