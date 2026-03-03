# 踩坑记录与经验总结

本文档记录项目实践中的常见问题、错误模式与解决方案，帮助开发者与 AI agent 避免重复踩坑。

> **维护约定**: 每次发现新的踩坑场景时，应追加到本文档对应分类下，并在 `.claude/copilot-instructions.md` 中引用本文档。

---

## 目录

1. [文件路径与命名](#1-文件路径与命名)
2. [API 调用与参数](#2-api-调用与参数)
3. [JSON 与数据结构](#3-json-与数据结构)
4. [生文 API 使用](#4-生文-api-使用)
5. [生图 API 使用](#5-生图-api-使用)
6. [Python 代码执行](#6-python-代码执行)
7. [共享数据协议](#7-共享数据协议)
8. [文件格式与编码](#8-文件格式与编码)

---

## 1. 文件路径与命名

### 1.1 图片资源路径必须使用完整相对路径

**问题**:
调用生图 API 时使用短路径 `assets/char_ref_小益_v1.png` 导致 `reference_images` 无法访问。

**原因**:
MCP 生图服务需要从当前工作目录定位文件，短路径可能在服务端解析失败。

**正确做法**:
```python
# ❌ 错误
reference_images = ["assets/char_ref_小益_v1.png"]

# ✅ 正确
reference_images = ["scripts/电梯迷失/assets/char_ref_小益_v1.png"]
```

**适用场景**: 所有调用 `mcp__playwright-image-gen__generate_image` 时的 `reference_images` 参数。

---

### 1.2 路径回写前必须核验文件实际存在

**问题**:
按角色名推断文件名（如 `char_小益_calm.png`），但实际生成文件名为 `char_小益_calm.png`（拼写差异），导致路径悬空。

**原因**:
汉字输入法可能产生不同编码或拼写，生图 API 返回文件名与推断不一致。

**正确做法**:
```python
import glob
import os

# ❌ 错误：按角色名推断
character_image = f"assets/char_{char_name}_calm.png"

# ✅ 正确：从磁盘读取实际文件名
actual_files = glob.glob(f"scripts/{script_name}/assets/char_{char_name}_*.png")
if actual_files:
    character_image = actual_files[0]  # 使用实际返回的文件名
```

**适用场景**: `generate-scene-assets` 输出 `asset_manifest` 时，`attach-script-assets` 回写路径前。

---

### 1.3 segment_id 必须使用段落 id 字段值，不得使用数组索引

**问题**:
在 `asset_manifest` 中使用 `"segment_id": "0"` 而非 `"segment_id": "s1"`，导致回写时无法匹配段落。

**原因**:
数组索引是内部实现细节，剧本结构依赖 `segments[i].id` 字段（如 `"s1"`, `"s2"`）。

**正确做法**:
```python
# ❌ 错误：使用数组索引
manifest.append({"segment_id": str(idx), "background_image": bg_path})

# ✅ 正确：使用段落 id 字段值
manifest.append({"segment_id": segment["id"], "background_image": bg_path})
```

**适用场景**: `generate-scene-assets` 构建 `asset_manifest` 时。

---

## 2. API 调用与参数

### 2.1 混元生文 API 必须设置 enable_deep_read=false

**问题**:
调用 `mcp__playwright-image-gen__generate_text` 时传入 `enable_deep_read=true`，导致 `InvalidParameter` 报错。

**原因**:
深度阅读功能默认未开通，传 `true` 会触发服务端限制。

**正确做法**:
```python
result = mcp__playwright-image-gen__generate_text(
    prompt="...",
    context_files=["planning_draft.txt"],
    enable_deep_read=False  # 必须为 False 或不传
)
```

**适用场景**: 所有调用混元生文 API 且需要文件上下文的场景。

---

### 2.2 混元文件接口仅支持 .txt 格式

**问题**:
上传 `planning_draft.md` 到 `context_files`，导致 `InvalidParameterValue` 错误。

**原因**:
混元文件接口仅接受 `.txt` 格式，不支持 `.md`。

**正确做法**:
```python
# 1. 先保存 .md 副本（可读性）
with open("scripts/电梯迷失/drafts/planning_draft.md", "w", encoding="utf-8") as f:
    f.write(planning_text)

# 2. 再保存 .txt 副本（API 上传用）
with open("scripts/电梯迷失/drafts/planning_draft.txt", "w", encoding="utf-8") as f:
    f.write(planning_text)

# 3. 调用时传 .txt 路径
context_files = ["scripts/电梯迷失/drafts/planning_draft.txt"]
```

**适用场景**: 所有需要通过 `context_files` 上传草稿的场景。

---

### 2.3 生图 API 提示词过长会导致调用失败

**问题**:
角色设定图提示词超过 2000 字符，导致 API 返回错误。

**原因**:
混元生图 API 对 prompt 长度有限制。

**正确做法**:
- 优先使用中文关键词（更紧凑）
- 分层描述但保持简洁："角色特征 + 服装 + 构图 + 风格"
- 避免冗余修饰词，每个要素用 2-5 个词概括

```python
# ❌ 错误：过长提示词
prompt = "一位年轻的办公室职员，她的年龄大约25岁左右，有着一头棕色的长发，穿着休闲的衬衫和裤子，表情看起来有些粗心大意的样子，整体给人一种随性的感觉，画面采用三视图构图，包含正面、侧面和背面，线条清晰，色彩柔和，符合二次元视觉小说角色设定单的标准，背景干净简洁，没有多余元素，光影自然，细节丰富但不过度..."

# ✅ 正确：精简关键词
prompt = "25岁办公职员，棕色长发，休闲衬衫，粗心表情，三视图，清晰线条，二次元视觉小说风格"
```

**适用场景**: 所有调用生图 API 的场景。

---

### 2.4 图生图必须确保 reference_images 为 URL 或已上传 COS

**问题**:
直接传本地路径到 `SubmitTextToImageJob` 的 `reference_images`，导致 API 无法访问。

**原因**:
图生图接口要求参考图可通过 `https` 访问。

**正确做法**:
- 若 `COS_AUTO_UPLOAD_ENABLED=true`：MCP 服务自动上传并返回 URL
- 若未启用 COS：必须先手动上传到公开可访问位置

```python
# ✅ 使用完整相对路径，MCP 服务自动上传
reference_images = ["scripts/电梯迷失/assets/char_ref_小益_v1.png"]
```

**适用场景**: `generate-scene-assets` 生成角色立绘时。

---

## 3. JSON 与数据结构

### 3.1 JSON 写入必须使用 json.dumps，禁止手工拼接

**问题**:
手工拼接 JSON 字符串导致中文引号 `"` `"` 等非法字符，解析失败。

**原因**:
输入法可能插入全角引号，手工拼接无法保证格式正确。

**正确做法**:
```python
import json

# ❌ 错误：手工拼接
json_str = '{"title": "' + title + '", "description": "' + desc + '"}'

# ✅ 正确：使用 json.dumps
data = {"title": title, "description": desc}
json_str = json.dumps(data, ensure_ascii=False, indent=2)

with open("script.json", "w", encoding="utf-8") as f:
    f.write(json_str)
```

**适用场景**: 所有写入 JSON 文件的场景。

---

### 3.2 display_break_lines 必须为字符串数组，text 必须留空

**问题**:
同时设置 `text` 和 `display_break_lines`，导致内容重复。

**原因**:
引擎按步累积 `display_break_lines`，若 `text` 非空会重复显示。

**正确做法**:
```json
{
  "id": "s1",
  "text": "",
  "display_break_lines": [
    "午夜时分，你独自站在空荡站台。",
    "远处传来列车鸣笛，雾气逐渐逼近。"
  ]
}
```

**适用场景**: `create-script` 和 `configure-script-presentation` 生成段落配置时。

---

### 3.3 text 字段禁止包含 \n，分行由 display_break_lines 控制

**问题**:
在 `text` 字段中使用 `\n` 换行，导致渲染异常。

**原因**:
引擎不解析 `\n`，分行完全由 `display_break_lines` 控制。

**正确做法**:
```python
# ❌ 错误
segment["text"] = "第一行\n第二行"

# ✅ 正确：使用 display_break_lines
segment["text"] = ""
segment["display_break_lines"] = ["第一行", "第二行"]
```

**适用场景**: `create-script` 生成段落时。

---

## 4. 生文 API 使用

### 4.1 阶段2 必须注入 planning_draft 全文，且落盘时须同时保存 .txt 副本

**问题**:
仅传简短摘要给生文 API，导致正文与规划不一致；或者落盘时只保存了 `.md` 而没有 `.txt` 副本，导致无法通过 `context_files` 上传，被迫退回 inline 注入（写入 `system_prompt`）。

**原因**:
- 生文 API 无法凭空记忆之前的规划，必须显式传入全文。
- 混元 `context_files` 仅支持 `.txt` 格式（详见 § 2.2），若只有 `.md` 则无法上传。
- Inline 注入 (`system_prompt`) 在内容短时可行，但随正文增长会超出消息长度限制，且不如文件上下文稳定。

**正确做法**:
阶段1落盘时必须同时写 `.md` 和 `.txt` 两个副本：

```python
planning_text = "..."  # 生文 API 返回内容

# 1. 落盘 .md（可读性）
with open("scripts/<name>/drafts/planning_draft.md", "w", encoding="utf-8") as f:
    f.write(planning_text)

# 2. 落盘 .txt（context_files 上传用）
with open("scripts/<name>/drafts/planning_draft.txt", "w", encoding="utf-8") as f:
    f.write(planning_text)
```

阶段2调用生文 API 时通过 `context_files` 注入：

```python
result = mcp_playwright-im_generate_text(
    prompt="请基于规划草稿生成第一章正文...",
    context_files=["scripts/<name>/drafts/planning_draft.txt"],
    session_id="novel_draft_session",
    use_session_history=True,
    carry_forward_file_ids=True
)
```

**适用场景**: `create-script` 阶段1落盘、阶段2 所有生文调用。

---

### 4.2 长篇续写必须使用 session_id + use_session_history=true

**问题**:
每批续写都创建新会话，导致后续批次丢失前文上下文。

**原因**:
混元生文 API 默认无状态，需要 `session_id` 保持上下文。

**正确做法**:
```python
session_id = "novel_draft_20260303"

# 第一批
result1 = mcp__playwright-image-gen__generate_text(
    prompt="生成第1-10段...",
    session_id=session_id,
    use_session_history=True
)

# 第二批（自动继承前文上下文）
result2 = mcp__playwright-image-gen__generate_text(
    prompt="继续第11-20段...",
    session_id=session_id,
    use_session_history=True
)
```

**适用场景**: `create-script` 分批生成长篇正文时。

---

### 4.3 超长上下文必须使用 context_files + carry_forward_file_ids=true

**问题**:
`planning_draft` + 已生成正文超过 30k token，单次消息截断。

**原因**:
混元消息长度有限制，需要文件上下文模式。

**正确做法**:
```python
# 第一批：上传 planning_draft
result1 = mcp__playwright-image-gen__generate_text(
    prompt="生成第1-20段...",
    context_files=["scripts/电梯迷失/drafts/planning_draft.txt"],
    session_id=session_id,
    use_session_history=True,
    carry_forward_file_ids=True  # 默认 True，后续批次自动继承
)

# 第二批：无需重复传 context_files
result2 = mcp__playwright-image-gen__generate_text(
    prompt="继续第21-40段...",
    session_id=session_id,
    use_session_history=True  # 自动继承 FileIDs
)
```

**适用场景**: `create-script` 长篇正文续写超出消息长度限制时。

---

### 4.4 阶段2 正文草稿必须为"叙事+对话混合"，禁止纯对白

**问题**:
生成正文全篇为"角色名：台词"格式，缺少描写层。

**原因**:
视觉小说需要人物/环境/心理描写，纯对白无法满足叙事要求。

**正确做法**:
```python
# 提示词中必须显式要求
prompt = """
请生成视觉小说正文，必须包含：
1. 人物描写（动作、神态、语气）
2. 环境描写（场景、时间、氛围）
3. 心理描写（当下动机、情绪变化）
4. 对话（作为叙事组成部分，不超过 30%）

禁止全篇纯对白格式。
"""
```

**自检**:
若检测到草稿为纯对白，必须重新调用生文 API。

---

## 5. 生图 API 使用

### 5.1 背景图必须显式约束"无人物"

**问题**:
生成的背景图出现人物剪影或远景人影。

**原因**:
未在提示词中显式排除人物，生图模型可能生成人物元素。

**正确做法**:
```python
prompt = "商场电梯口，现代风格，明亮灯光，透视构图，无人场景，no people, no character"
negative_prompt = "低质量, 模糊, 水印, 文本, 人物, 人影, 角色"

# 调用时设置
scene_type = "background"
strict_no_people = True
```

**适用场景**: `generate-scene-assets` 生成背景图时。

---

### 5.2 同一剧本必须共享统一 style_anchor

**问题**:
每张背景图使用不同提示词，导致画风不一致。

**原因**:
生图模型对提示词敏感，需要统一风格锚点。

**正确做法**:
```python
# 在 shared.style_contract 中定义
style_contract = {
    "background_style_anchor": "anime visual novel background, clean lineart, soft global illumination, cinematic composition",
    "background_negative_anchor": "低质量, 模糊, 水印, 文本, 人物, 人影"
}

# 所有背景图 prompt 统一拼接
prompt = f"{scene_desc}, {style_contract['background_style_anchor']}"
```

**适用场景**: `generate-scene-assets` 生成同一剧本的多张背景图时。

---

### 5.3 角色立绘必须使用图生图（混元 3.0），禁止退回文生图

**问题**:
角色立绘使用 `TextToImageLite` 纯文生图，导致不同段落的同角色外观不一致。

**原因**:
纯文生图无法保证角色一致性，必须以角色设定图为参考。

**正确做法**:
```python
# ✅ 正确：使用图生图
result = mcp__playwright-image-gen__generate_image(
    script_name="电梯迷失",
    prompt="小益站在电梯口，尴尬表情，半身构图",
    filename="char_小益_embarrassed.png",
    width=720,
    height=1280,
    api_action="SubmitTextToImageJob",  # 强制使用图生图
    scene_type="character",
    reference_images=["scripts/电梯迷失/assets/char_ref_小益_v1.png"]
)
```

**适用场景**: `generate-scene-assets` 生成角色立绘时。

---

### 5.4 角色立绘分辨率必须为竖向（720x1280）

**问题**:
立绘使用横向分辨率（1280x720），导致人物构图异常。

**原因**:
视觉小说立绘需要竖向构图（半身/全身），横向会压缩人物。

**正确做法**:
```python
# ❌ 错误
width, height = 1280, 720

# ✅ 正确
width, height = 720, 1280
```

**适用场景**: `generate-scene-assets` 生成角色立绘时。

---

## 6. Python 代码执行

### 6.1 避免创建临时 Python 脚本，优先使用内联 python -c

**问题**:
为简单操作创建多个临时 `.py` 文件（如 `convert_to_segments.py`, `update_segments.py`），增加文件管理负担。

**原因**:
Claude Code 可通过 Pylance 直接执行 Python 代码，无需创建临时文件。

**正确做法**:
```bash
# ❌ 错误：创建临时脚本
cat > convert_to_segments.py <<'EOF'
import json
...
EOF
python convert_to_segments.py

# ✅ 正确：使用内联 python -c
python -c "
import json
with open('script.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
# 后续处理...
with open('script.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
"
```

**适用场景**: 所有一次性 JSON 操作、简单数据转换任务。

**例外**: 若脚本需要在多个项目中复用（如 `iterate-skills`），可创建为正式工具。

---

### 6.2 复杂逻辑使用 heredoc 提高可读性

**问题**:
长 Python 代码压缩成单行 `-c`，难以阅读和调试。

**原因**:
`python -c` 适合简单操作，复杂逻辑需要多行格式。

**正确做法**:
```bash
python <<'EOF'
import json
import glob

with open('script.json', 'r', encoding='utf-8') as f:
    script = json.load(f)

# 复杂处理逻辑
for segment in script['segments']:
    if segment.get('speaker') == '小益':
        segment['character_image'] = 'assets/char_小益_calm.png'

with open('script.json', 'w', encoding='utf-8') as f:
    json.dump(script, f, ensure_ascii=False, indent=2)
EOF
```

**适用场景**: 需要多行逻辑、循环、条件判断的场景。

---

## 7. 共享数据协议

### 7.1 所有 skill 必须读取 shared，写回时必须保留其他字段

**问题**:
某 skill 仅写回 `shared.asset_manifest`，清空了 `shared.planning` 和 `shared.character_refs`。

**原因**:
未保留已有字段，覆盖写入导致数据丢失。

**正确做法**:
```python
# 1. 先读取完整 shared
with open('script.json', 'r', encoding='utf-8') as f:
    script = json.load(f)
    shared = script.get('shared', {})

# 2. 更新目标字段
shared['asset_manifest'] = new_manifest
shared['pipeline_state']['stage'] = '4_completed'

# 3. 写回时保留其他字段
script['shared'] = shared
with open('script.json', 'w', encoding='utf-8') as f:
    json.dump(script, f, ensure_ascii=False, indent=2)
```

**适用场景**: 所有读写 `shared` 的 skill。

---

### 7.2 pipeline_state 更新必须包含 stage 和 updated_at

**问题**:
仅更新 `stage`，未更新 `updated_at` 时间戳。

**原因**:
时间戳用于追踪流程进度，缺失会影响调试。

**正确做法**:
```python
from datetime import date

shared['pipeline_state'] = {
    'stage': '4_completed',
    'updated_at': date.today().isoformat(),  # 2026-03-03
    'assets_attached': {...}
}
```

**适用场景**: 所有更新 `pipeline_state` 的场景。

---

## 8. 文件格式与编码

### 8.1 所有 Python 文件必须声明 UTF-8 编码

**问题**:
中文注释或字符串在某些环境下乱码。

**原因**:
未显式声明编码，Python 默认使用系统编码（可能为 GBK）。

**正确做法**:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 后续代码...
```

**适用场景**: 所有包含中文的 Python 脚本。

---

### 8.2 JSON 文件必须使用 UTF-8 无 BOM 编码

**问题**:
JSON 文件保存为 UTF-8 with BOM，导致解析失败。

**原因**:
BOM 字节序标记会被解析器识别为非法字符。

**正确做法**:
```python
# Python 默认写入 UTF-8 无 BOM
with open('script.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

**适用场景**: 所有写入 JSON 文件的场景。

---

## 贡献指南

发现新的踩坑经历时，请按以下格式追加到对应分类：

```markdown
### X.Y 问题简述（一句话）

**问题**:
详细描述错误现象。

**原因**:
解释为什么会出现这个问题。

**正确做法**:
```代码示例或操作步骤
```

**适用场景**: 说明哪些情况下需要注意。
```

---

### 5.5 混元3.0支持AI自动优化提示词

**功能**:
混元3.0生图接口（`SubmitTextToImageJob`）支持 `Revise` 参数（工具层面为 `revise_prompt`）自动优化提示词，开启后AI会自动扩展和优化提示词以提升生成质量。

**用法**:
```python
result = mcp__playwright-image-gen__generate_image(
    script_name="测试剧本",
    prompt="竹林小路，夜晚",
    filename="scene_forest.png",
    api_action="SubmitTextToImageJob",
    revise_prompt=True,  # 开启AI优化（默认True）
    logo_add=0  # 不添加水印（默认0）
)
```

**效果**:
- 开启后，模型会自动扩展和优化你的提示词以提升生成质量
- 例如："竹林小路，夜晚" 可能被优化为 "竹林间幽静的小路，月光透过竹叶洒落，夜色朦胧，电影感构图，高清细节"

**适用场景**: 使用混元3.0生成背景图或角色立绘时，建议开启以提升画质。

---

### 1.4 生图 API 会将 script_name 中的特殊字符替换为下划线，导致落盘目录与预期不符

**问题**:
调用生图 API 时传入 `script_name="励志打遍天下无敌手——我是指街霸6"`（含全角破折号 `——`），实际落盘目录变为 `scripts/励志打遍天下无敌手_我是指街霸6/assets/`（`——` 被替换为 `_`），与剧本主目录 `励志打遍天下无敌手——我是指街霸6` 不一致，产生两个目录。

**原因**:
MCP 生图服务在处理 `script_name` 时会将部分特殊字符（如全角破折号 `——`）转义为下划线，以生成合法文件系统路径。

**正确做法**:
生图 API 调用完成后，立即用 Python 将图片从下划线目录复制到正确目录，再删除多余目录：

```python
import os, shutil

src = r"scripts/励志打遍天下无敌手_我是指街霸6/assets"
dst = r"scripts/励志打遍天下无敌手——我是指街霸6/assets"

for fname in os.listdir(src):
    shutil.copy2(os.path.join(src, fname), os.path.join(dst, fname))

shutil.rmtree(os.path.dirname(src))  # 删除多余目录
```

或在剧本命名阶段主动避免全角特殊字符（破折号、省略号等）。

**适用场景**: 剧本名称包含全角破折号 `——`、省略号 `……` 等特殊字符时，所有生图 API 调用后应核对落盘路径。

---

**最后更新**: 2026-03-03
**文档版本**: v1.0
