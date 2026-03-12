# 踩坑记录与经验总结

本文档记录项目实践中的常见问题、错误模式与解决方案，帮助开发者与 AI agent 避免重复踩坑。

> **维护约定**: 每次发现新的踩坑场景时，应追加到本文档对应分类下，并在 `.claude/copilot-instructions.md` 中引用本文档。

---

## 目录

0. [剧本生产最小基线（必读）](#0-剧本生产最小基线必读)
1. [文件路径与命名](#1-文件路径与命名)
2. [API 调用与参数](#2-api-调用与参数)
3. [JSON 与数据结构](#3-json-与数据结构)
4. [生文 API 使用](#4-生文-api-使用)
5. [生图 API 使用](#5-生图-api-使用)
6. [Python 代码执行](#6-python-代码执行)
7. [共享数据协议](#7-共享数据协议)
8. [文件格式与编码](#8-文件格式与编码)
9. [环境配置与初始化](#9-环境配置与初始化)

---

## 0. 剧本生产最小基线（必读）

为避免 agent 因历史补丁语句产生误解，剧本生产默认按以下基线执行：

1. 模块1/2 文本必须调用生文 API（禁止离线直写全文）。
2. `shared` 是唯一共享数据源；写回必须保留非目标字段。
3. `display_break_lines` 为可选节奏手法；使用时必须字符串数组且 `text=""`。
4. `effect` 为可选演出手法；若 `effect=typewriter`，`speed=55`。
5. 模块2结束必须通过双门禁：
    - 本地门禁：`python tools/check_script_quality.py scripts/<name>/script.json --min-narration-ratio 0.45 --json`
    - 模型门禁：调用 `review-script`，按 0-10 分制和 `delivery_gate` 判定
6. 阶段2默认按“一个分镜一次生文调用”执行，禁止单次请求生成全量分镜。
7. 阶段3人物图必须两段式：先文生图三视图设定图，再图生图生成竖版剧情立绘。
8. 阅读器右侧 `character_image` 必须回写竖版立绘，不可直接使用三视图设定图。
9. 禁止读取其他剧本正文作为创作素材。
10. 质量修复顺序固定为：本地体检 → 本地修复 → 模型复评 → 定向改写（最多3轮）。
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

**补充**:
- 不要依赖默认值，务必显式传 `enable_deep_read=false`。
- 若开启 `context_files` 时报 `InvalidParameter`，先检查是否隐式启用了深度阅读。

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

### 2.5 评分剧本必须使用文件上传，禁止直接写入提示词

**问题**:
将完整剧本内容（97段）直接拼接到提示词中，导致提示词长度超过 API 限制或 token 消耗过大。

**原因**:
视觉小说剧本通常包含数十甚至上百个段落，总字符数可达数万字，直接放入提示词会超出 token 上限。

**正确做法**:
1. 将剧本 JSON 转换为结构化文本格式
2. 保存为 `.txt` 文件（混元文件接口仅支持 `.txt` 格式）
3. 通过 `context_files` 参数上传文件
4. 提示词中仅包含评分要求和输出格式说明

```python
# ✅ 正确：使用文件上传
# 1. 生成剧本文本文件
review_input_path = script_path.parent / "review_input.txt"
with open(review_input_path, "w", encoding="utf-8") as f:
    f.write(f"# 剧本标题\n{script['title']}\n\n")
    f.write(f"# 剧本描述\n{script['description']}\n\n")
    # ... 写入 planning、segments 等完整内容

# 2. 调用生文 API
result = mcp_playwright-im_generate_text(
    prompt="请对上传的剧本文件进行多维度评分与分析...",
    system_prompt="你是资深视觉小说编剧与文学评论家...",
    context_files=[str(review_input_path)],
    enable_deep_read=False,
    temperature=0.3
)

# ❌ 错误：直接拼接到提示词
prompt = f"剧本内容：\n{json.dumps(script, ensure_ascii=False)}\n\n请评分..."
```

**适用场景**: `review-script` skill 评测剧本时；任何需要处理长文本输入的场景。

---

### 2.6 COS 桶地域与 COS_REGION 不一致会触发 NoSuchBucket

**问题**:
`context_files` 上传时报错 `NoSuchBucket`，即使 `COS_BUCKET` 已填写。

**原因**:
桶在上海地域，但配置仍为 `COS_REGION=ap-guangzhou`，请求发到了错误地域端点。

**正确做法**:
```json
// .vscode/mcp.json
"COS_AUTO_UPLOAD_ENABLED": "true",
"COS_BUCKET": "aiproject-1302501881",
"COS_REGION": "ap-shanghai"
```

**适用场景**: 使用 `context_files` 或 `reference_images` 上传本地文件到 COS 再调用混元 API 时。

---

### 2.7 同一 session 并发续写会触发 system 消息顺序错误

**问题**:
在复用同一个 `session_id` 时并行发起多次续写请求，返回 `Messages 中 system 角色必须位于列表的最开始`。

**原因**:
会话历史被并发写入，服务端合并消息时顺序冲突。

**正确做法**:
```python
# ❌ 错误：同 session 并发续写
parallel([
    generate_text(session_id="regress_x", ...),
    generate_text(session_id="regress_x", ...),
])

# ✅ 正确：同 session 串行续写，或改为不同 session 并行
generate_text(session_id="regress_x", ...)
generate_text(session_id="regress_x", ...)
```

**适用场景**: 模块1/2 按批次续写同一剧本时。

---

### 2.8 分镜规划器禁止绑定旧题材关键词映射

**问题**:
`plan_storyboards_from_novel.py` 在新题材上输出旧项目标题/背景（如重复“真相浮现”或历史 `assets/rain_fortune_stall.png`）。

**原因**:
规划器内部残留旧案例关键词到标题/背景的硬编码映射。

**正确做法**:
1. 优先按章节标题切分（如 `第一章 ...`）生成分镜。
2. 背景路径使用语义标签规则生成通用名，例如 `assets/scene_3_rain_night_morning.png`。
3. 保留段落评分切片作为无章节文本的兜底方案。

**适用场景**: 模块2前置分镜草案生成。

---

### 3.1 模块2写回前必须清洗“前置括号”和“章节标题泄漏”

**问题**:
剧本段落中出现 `（低声）这次我会...` 这类前置括号提示，或直接出现 `### 第一章 雨夜回访` 这类章节标题行。

**原因**:
生文结果混入舞台提示与章节标记，若不在模块2落盘前清洗，会直接污染阅读器正文显示。

**正确做法**:
1. 对非旁白段，去除开头短括号提示（如 `（低声）` / `(低声)`）。
2. 去除段落开头的章节标题行（支持 `### 第一章 ...` 与 `第一章 ...`）。
3. 清洗后若段落为空，跳过该段，避免写入空噪声段。

**适用场景**: 模块2 `normalize_and_repair_script` 落盘前。

---

### 7.1 自动修复停止条件不能只看 error

**问题**:
`auto_refine_script.py` 输出 `final_passed=True`，但仍存在 `SB_NARRATION_RATIO_LOW`，导致“门禁看似通过，单分镜仍失衡”。

**原因**:
修复器仅以“无 error”作为停止条件，没有把分镜级旁白比例告警纳入停止门槛。

**正确做法**:
在 `refine_script_until_pass` 中把 `SB_NARRATION_RATIO_LOW` 与 `GLOBAL_NARRATION_RATIO_LOW` 纳入停止条件：
- 只有“无 error + 无旁白占比告警 + 全局旁白占比达标”才允许停止。

**适用场景**: 模块2质量闭环、批量自动修复。

---

### 2.7 生图并发会触发 JobNumExceed，需改为串行队列

**问题**:
并行调用多个生图任务时，接口返回 `RequestLimitExceeded.JobNumExceed`，部分图片生成失败。

**原因**:
当前账号存在同类任务并发上限（常见为 1），批量并发提交会被服务端拒绝。

**正确做法**:
```python
# ❌ 错误：并发提交多个生图任务
for task in tasks:
    submit_async(task)

# ✅ 正确：串行提交，失败后重试当前任务
for task in tasks:
    ok = False
    for _ in range(3):
        ok = submit_once(task)
        if ok:
            break
    if not ok:
        raise RuntimeError("image generation failed")
```

**适用场景**: 背景图/立绘批量生成（`TextToImageLite`、`SubmitTextToImageJob`）时。

---

### 2.8 生文大上下文易超时，需保留降级模型与重试策略

**问题**:
模块2在上传完整 `novel_full.txt` 后，`hunyuan-pro` 多次出现 `Read timed out`，导致剧本转换中断。

**原因**:
上下文文件较大时，请求链路和生成耗时都上升，默认超时窗口下容易失败。

**正确做法**:
```python
# 1) 先按主模型请求
resp = generate_text(model="hunyuan-pro", context_files=[".../novel_full.txt"], retry_max=2)

# 2) 若连续超时，降级到轻量模型继续产出
if not resp["success"]:
    resp = generate_text(model="hunyuan-lite", context_files=[".../novel_full.txt"], retry_max=2)
```

**适用场景**: 阶段1/2 长文本生成或转换，且 `context_files` 使用完整正文时。

---

### 2.9 模型复评分制已切换为 0-10，禁止继续使用旧的 70 分门槛

**问题**:
模块2复评已经输出 `overall_score=6.6`、各维度 0-10 分，但编排层仍按“>=70 分通过”的旧口径判断，导致 agent 无法稳定停止迭代。

**原因**:
历史 AI 评分工具使用过 0-100 分制，后续 `review-script` 改为直接输出 0-10 分制 JSON，文档和 skill 没有同步清理旧阈值。

**正确做法**:
```text
# 新口径
- quality_gate: 模型原始结论
- delivery_gate: 编排统一结论

若同时满足：
overall_score >= 6.5
story_completeness >= 7
visual_novel_adaptation >= 7
其余核心维度 >= 6
且本地门禁通过

则可判定为 pass_with_polish，允许进入模块3。
```

**适用场景**: `generate-script`、`review-script`、`orchestrate-script-production` 的模块2闭环。

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

**适用场景**: `generate-script` 和 `configure-script-presentation` 生成段落配置时。

**补充（2026-03-04）**:
- 旧脚本常出现 `"display_break_lines": [1]`（整数断点旧格式），会导致节奏控制退化。
- 回写前必须做结构校验：若 `text` 非空则拆成字符串行数组写入 `display_break_lines`，并将 `text` 置空。

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

**适用场景**: `generate-script` 生成段落时。

---

### 3.4 编排阶段2必须运行 normalize 收尾门禁

**问题**:
生成剧本时遗漏 `display_break_lines` 新格式，落成旧结构（如 `[1]`）并混用 `text`。

**原因**:
流程只有约束描述，没有“写回后自动校验”执行步骤。

**正确做法**:
```bash
python scripts/normalize_script_break_lines.py scripts/<script_name>/script.json
python scripts/normalize_script_break_lines.py scripts/<script_name>/script.json --check
```

**适用场景**: `orchestrate-script-production` 模块2结束后，进入模块3之前。

---

### 3.5 display_break_lines 是节奏手法，不是每段强制字段

**问题**:
将 `display_break_lines` 误当作“每段必填”，导致短过渡段也被强行拆分，阅读节奏反而变碎。

**原因**:
把结构正确性约束误解成“所有段都必须多步显示”。

**正确做法**:
```json
// 短段：单步显示（可不写 display_break_lines）
{ "text": "封锁启动。", "effect": "typewriter", "speed": 55 }

// 重点段：同段多步点击推进
{ "text": "", "display_break_lines": ["第一句", "第二句"] }
```

**适用场景**: 视觉小说文本编排；需要在“可读性”和“节奏感”之间平衡时。

---

### 3.6 旧断点 `[1]` 与 `text` 并存时，转换必须优先保留 `text`

**问题**:
批量规范化把旧格式 `[1]` 直接转成 `['1']`，并清空 `text`，导致段落正文丢失，看起来像“没有文字动画”。

**原因**:
转换逻辑先使用了旧断点数组，而不是使用 `text` 里的真实句子。

**正确做法**:
```python
if has_display_break_lines and has_text:
    lines = [line.strip() for line in text.split("\\n") if line.strip()]
    segment["text"] = ""
    segment["display_break_lines"] = lines
```

**适用场景**: 历史剧本从旧断点格式迁移到字符串数组格式时。

---

### 3.7 `effect` 是可选演出字段，配置时必须合法

**问题**:
将 `effect` 写成 `"effect": {}` 等非法结构，导致文字动画表现异常或看起来“没有动画”。

**原因**:
将演出手法误当作固定结构字段，缺少“仅在配置时校验”的约束。

**正确做法**:
```python
effect = segment.get("effect")
if effect is not None and effect not in ("typewriter", "shake"):
    raise ValueError("effect 非法：仅允许 typewriter/shake，或不配置")
```

**适用场景**: 剧本演出编排阶段；需要配置动画时的字段校验。

---

### 3.8 使用 `typewriter` 时必须固定 `speed=55`

**问题**:
同为 `typewriter` 的段落速度不一致，导致阅读节奏忽快忽慢。

**原因**:
将 `typewriter` 也当作可自由调速，未应用统一节奏基线。

**正确做法**:
```python
if segment.get("effect") == "typewriter":
    segment["speed"] = 55
```

**适用场景**: 所有设置了 `effect=typewriter` 的段落。

---

### 3.9 模型返回 JSON 常见“协议近似正确”，落盘前必须二次校正

**问题**:
模型可能返回“看起来像 JSON”但不满足协议细节，例如：
- `next` 链不完整或提前 `null`
- 末段空文本
- 夹带未约定字段

**原因**:
大模型会优先满足语义要求，但不保证百分百满足严格结构约束。

**正确做法**:
```python
# 落盘前执行协议修复
# 1) 校正 id 连续性和 next 链
# 2) 移除未约定字段
# 3) 补齐末段有效 text
# 4) 再执行门禁校验
```

**适用场景**: `generate-script` 与 `orchestrate-script-production` 在写回 `script.json` 前。

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

**适用场景**: `generate-novel` 模块1落盘、`generate-script` 模块2 所有生文调用。

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

**适用场景**: `generate-novel` 分批生成长篇正文时。

---

### 4.2.1 AI 自评易虚高，必须启用严格评审提示词与硬门槛

**问题**:
同一模型可在创作后给出偏乐观评分，导致低质量文本被误判为“可用”。

**原因**:
默认评审提示词偏“鼓励式反馈”，且缺少硬门槛与证据约束，模型会倾向给中高分。

**正确做法**:
```python
# 1) 严格评审提示词（禁止鼓励式）
result = mcp_playwright-im_generate_text(
    prompt="严格评审：strengths<=2, weaknesses>=5, 每条缺点要有段落证据...",
    context_files=["scripts/<name>/review_input.txt"],
    temperature=0.2
)

# 2) 硬门槛
# overall>=6.8 且 literary>=6 且 character>=6 且 creativity>=6
# 不达标 -> 定向重写 -> 再评审（最多2轮）
```

**适用场景**: 阶段2正文生成后的质量验收与自动重写闭环。

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

**适用场景**: `generate-novel` 长篇正文续写超出消息长度限制时。

---

### 4.4 脚本评估（quality_score_by_ai）必须通过 COS 上传脚本文件

**问题**:
将整个脚本内容（几千行 JSON）嵌入 prompt，导致消息长度膨胀、token 浪费、响应变慢。

**原因**:
脚本 JSON 可能包含数十个段落，直接 inline 会占用大量 prompt token；应该把文件上传到 COS，混元 API 通过 `context_files` 访问。

**正确做法**:
```python
# ❌ 错误：直接嵌入脚本内容
result = mcp_playwright-im_generate_text(
    prompt=f"请评估脚本：{very_long_script_json}...",
)

# ✅ 正确：上传到 COS，通过 context_files 传递
# 1. 脚本先转为 .txt 副本（COS 仅支持 .txt）
script_txt_path = "scripts/<name>/script.txt"
with open(script_txt_path, "w", encoding="utf-8") as f:
    f.write(json.dumps(script_data, ensure_ascii=False, indent=2))

# 2. 上传到 COS（调用 upload_to_cos.py）
cos_url = upload_to_cos(script_txt_path)  # 返回公开 URL

# 3. 评估时只传元数据 + COS URL
result = mcp_playwright-im_generate_text(
    prompt="请评估脚本：标题《xxx》，共 N 段。详见上传的脚本文件。",
    context_files=[cos_url],  # 直接传 COS URL
    session_id="script_quality_audit"
)
```

工具 `quality_score_by_ai.py` 已内置 COS 上传逻辑：
```bash
python scripts/quality_score_by_ai.py scripts/<name>/script.json
# 自动 → upload_to_cos.py → COS URL → context_files → 混元 API
```

**适用场景**: `quality_gate_ai.py`（AI 质量门）、`review-script`（剧本评分）、任何向混元 API 上传脚本进行评估的场景。

**收益**:
- Prompt token 节省 50-80%（脚本字数多时）
- API 响应更快（消息队列压力降低）
- 遵循 COS 最佳实践，降低网络成本

---

### 4.5 阶段2 正文草稿必须为"叙事+对话混合"，禁止纯对白

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

### 6.3 剧本生产流程编排禁止新增专用 Python 脚本

**问题**:
将“小说→剧本→资产”流程实现为新的 Python 编排脚本，导致与 agent/skill 体系双轨并存、维护成本上升。

**原因**:
项目定位为 agent-first；流程控制应由 agent 通过文档约束与 skill 调用完成，不应再复制一套脚本编排层。

**正确做法**:
```text
# ❌ 错误：新增脚本编排入口
python scripts/pipeline_runner.py <script_name> all

# ✅ 正确：由 agent 按阶段执行
1) 先补阶段文档（输入/输出/验收）
2) 调用 generate-novel / generate-script / generate-scene-assets（可选：generate-character-images / attach-script-assets）
3) 完成后回写 DEVELOPMENT.md 与阶段文档
```

**适用场景**: 任何涉及剧本生产流水线重构、编排或阶段拆分的任务。

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

**固定收尾规则**:
每次生图批处理结束后，必须执行以下三步并作为阶段4完成条件：
1. 将 `scripts/<规范化名>/assets/*` 同步到 `scripts/<原剧本名>/assets/*`
2. 校验 `script.json` 中 `background.image/character_image` 指向的文件均存在
3. 删除 `scripts/<规范化名>/` 冗余目录，避免双目录长期并存

---

### 1.5 生图完成后未删除规范化目录会导致后续误读资产源

**问题**:
资产已复制到目标剧本目录，但未删除规范化目录（如 `scripts/因果循环_失落记忆的密码/`），后续流程可能错误读取旧目录。

**原因**:
`scripts/` 下同时存在“原名目录”和“规范化目录”，人工或脚本在扫描时可能命中错误目录。

**正确做法**:
```python
from pathlib import Path
import shutil

normalized_dir = Path("scripts/因果循环_失落记忆的密码")
if normalized_dir.exists():
    shutil.rmtree(normalized_dir)
```

**适用场景**: 任何存在 `script_name` 特殊字符替换导致双目录并存的剧本生产流程。

### 1.6 PowerShell 终端中含全角破折号的路径在 git pathspec 中被截断

**问题**:
在 PowerShell 中执行 `git add "scripts/励志打遍天下无敌手——我是指街霸6/"` 时，报错 `fatal: pathspec did not match any files`，全角破折号 `——` 被截断，实际传给 git 的路径变为 `scripts/励志打遍天下无敌手我是指街霸6/`。

**原因**:
PowerShell 终端对某些 Unicode 字符（全角破折号 U+2014/U+2015）在拼接 argv 时发生编码截断，git 接收到的路径不完整。

**正确做法**:
用 Python subprocess 以列表形式传参，绕过 shell 字符串解析：

```python
import subprocess
subprocess.run(["git", "add", "scripts/励志打遍天下无敌手——我是指街霸6/"],
               cwd=r"d:\AIProject\Playwright")
```

**适用场景**: 任何需要在 PowerShell 终端中对含全角特殊字符的路径执行 `git add / mv / rm` 等操作时。

---

## 9. 环境配置与初始化

### 9.1 Windows PowerShell 禁止运行脚本导致无法激活虚拟环境

**问题**:
Windows 系统默认禁止 PowerShell 运行未签名脚本，执行 `.venv\Scripts\Activate.ps1` 时报错 `UnauthorizedAccess` 或 `PSSecurityException`。

**原因**:
Windows PowerShell 默认执行策略为 `Restricted` 或 `AllSigned`，不允许运行本地未签名的脚本文件。

**正确做法**:

方案1（推荐）：修改当前用户执行策略
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

方案2：直接使用虚拟环境 Python，无需激活
```powershell
.venv\Scripts\python.exe main.py
```

方案3：临时绕过执行策略（仅当次有效）
```powershell
powershell -ExecutionPolicy Bypass -File .venv\Scripts\Activate.ps1
```

**适用场景**: 首次在 Windows 机器上使用虚拟环境，或在企业管理的 Windows 系统上开发 Python 项目。

**注意事项**:
- `RemoteSigned` 策略允许本地脚本运行，但从网络下载的脚本需要签名
- 只需设置一次，后续该用户账户下所有 PowerShell 会话都生效
- 如果不想修改执行策略，方案2（直接运行 python.exe）是最安全的选择

---

**最后更新**: 2026-03-11
**文档版本**: v1.0
