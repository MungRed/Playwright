---
name: review-script
description: 调用腾讯混元大模型对剧本进行评分与分析，输出改进建议并保存到剧本目录。关键词：评分, 评测, 审阅, review, rating, 剧本分析
---

## 功能说明

对指定或所有剧本进行智能评分与分析：
- 读取剧本 JSON 文件（metadata、segments、planning）
- 调用腾讯混元生文 API 进行多维度评分
- 生成改进建议与具体指导
- 保存评分报告到 `scripts/<script_name>/review.json`

## 评分维度

1. **故事完整性**（1-10）：剧情逻辑、叙事连贯性、开头结尾呼应
2. **角色塑造**（1-10）：人物性格鲜明度、对话符合人设、情感表达
3. **文学质量**（1-10）：语言表现力、描写细腻度、节奏把控
4. **视觉小说适配度**（1-10）：段落划分合理性、展示节奏、留白与想象空间
5. **创意与主题**（1-10）：独特性、主题深度、情感共鸣

## 输入参数

- `script_name`（可选）：指定剧本名称；若不传，则评测所有剧本
- `output_format`（可选）：`json`（默认）或 `markdown`
- `include_suggestions`（可选）：是否包含详细改进建议（默认 `true`）
- `strict_mode`（可选）：是否启用严苛评审模式（默认 `true`）
  - 开启后：禁止鼓励式措辞、禁止虚高分、`strengths` 最多 2 条、`weaknesses` 至少 5 条且需可定位证据

## 输出格式（review.json）

```json
{
  "script_name": "打倒群里的柚子厨",
  "reviewed_at": "2026-03-03T14:30:00",
  "model": "hunyuan-pro",
  "ratings": {
    "story_completeness": 8,
    "character_development": 7,
    "literary_quality": 7,
    "visual_novel_adaptation": 9,
    "creativity_theme": 8
  },
  "overall_score": 7.8,
  "summary": "轻松幽默的日常剧本，节奏流畅，人物互动自然...",
  "strengths": [
    "对话生动自然，贴合日常语境",
    "情绪曲线设计合理，从冲突到和解过渡自然"
  ],
  "weaknesses": [
    "部分段落缺乏环境描写，画面感略显单薄",
    "角色背景信息不足，人物形象较为扁平"
  ],
  "suggestions": [
    {
      "category": "环境描写",
      "priority": "medium",
      "description": "在关键情绪转折点增加场景细节，如群聊界面氛围、人物表情变化等",
      "example_segments": ["3", "12", "18"]
    },
    {
      "category": "角色深度",
      "priority": "high",
      "description": "通过简短独白或旁白补充角色性格侧写，让读者更理解角色动机",
      "example_segments": ["0", "5"]
    }
  ]
}
```

## 执行步骤

1. 确定评测范围：
   - 若传入 `script_name`，仅评测指定剧本
   - 否则扫描 `scripts/` 目录，排除 `shared`、`bootstrap_env.py`、`upload_to_cos.py`
   - 检查每个目录是否包含 `script.json`

2. 准备剧本文本文件：
   - 解析 `script.json` 的 `title`、`description`、`segments`
   - 提取 `shared.planning`（若存在）获取世界观、人设、大纲
   - 将剧本内容转换为结构化文本格式：
     ```
     # 剧本标题
     标题内容
     
     # 剧本描述
     描述内容
     
     # 世界观设定
     ...
     
     # 角色设定
     - 角色1: 人设描述
     - 角色2: 人设描述
     
     # 剧情大纲
     ...
     
     # 剧本段落（完整）
     === 段落 s1 ===
     文本内容...
     
     === 段落 s2 ===
     文本内容...
     ```
   - **必须保存为 `.txt` 文件**：`scripts/<script_name>/review_input.txt`（混元文件接口仅支持 `.txt` 格式）
   - 处理 `display_break_lines`：若段落有该字段，拼接为完整文本

3. 构建评分提示词（不含剧本内容）：
   - 系统角色：资深视觉小说编剧与文学评论家
   - 任务说明：对上传的剧本文件进行多维度评分与分析
   - 输出要求：严格 JSON 格式，包含所有评分维度、总分计算、优缺点列表、改进建议
   - **提示词中不包含剧本具体内容**，避免超长提示词问题

4. 调用生文 API（通过文件上传）：
   - 工具：`mcp_playwright-im_generate_text`
   - 参数：
     - `system_prompt`：角色与输出格式约束
     - `prompt`：评分要求与输出格式说明（不含剧本内容）
     - `context_files`：`["scripts/<script_name>/review_input.txt"]`（上传剧本文本文件）
     - `enable_deep_read`：`false`（默认未开通，详见 PITFALLS.md § 2.1）
     - `model`：默认 `hunyuan-pro`
     - `temperature`：0.3（评分需要稳定性）
   - 超时重试：`retry_max=2`

5. 解析与保存：
   - 解析 API 返回的 JSON 文本（若返回包含 markdown 代码块，需提取 JSON 部分）
   - 补充元数据：`reviewed_at`（ISO 8601 格式）、`model`、`script_name`
   - 保存到 `scripts/<script_name>/review.json`
   - 若 `output_format=markdown`，额外生成 `review.md` 摘要报告

6. 清理临时文件：
   - 删除 `scripts/<script_name>/review_input.txt`（可选，保留可用于调试）

7. 输出摘要：
   - 评测剧本数量
   - 每个剧本的总分与简要评语
   - 保存路径列表

## 约束与注意事项

- **不修改原剧本**：本 skill 仅读取与评分，不对 `script.json` 进行任何修改
- **文件格式约束**：剧本文本必须保存为 `.txt` 格式才能上传到混元文件接口（详见 PITFALLS.md § 2.2）
- **完整剧本评分**：通过 `context_files` 上传完整剧本文本，不再需要采样策略
- **严格评审默认开启**：默认 `strict_mode=true`，评审目标是发现问题而非安抚作者
- **证据约束**：每条主要缺点必须能回溯到 `example_segments`
- **评分一致性**：同一剧本多次评测应保持评分稳定（通过低 temperature 保证）
- **错误处理**：若剧本解析失败或 API 调用失败，记录错误并继续评测下一个剧本
- **并发控制**：串行评测，避免并发请求导致 API 限流
- **临时文件管理**：`review_input.txt` 可保留用于调试，也可在评测完成后删除

## 典型使用场景

1. **批量质量检测**：评测所有剧本，找出需要改进的低分项目
2. **单剧本深度分析**：针对新创作剧本进行详细评分与改进指导
3. **迭代对比**：修改剧本后重新评测，对比前后评分变化

## 示例调用（Python heredoc）

```python
python <<'EOF'
import json
from pathlib import Path
from datetime import datetime

# 读取剧本
script_path = Path("scripts/打倒群里的柚子厨/script.json")
with open(script_path, "r", encoding="utf-8") as f:
    script = json.load(f)

# 转换为文本格式
review_input = []
review_input.append(f"# 剧本标题\n{script['title']}\n")
review_input.append(f"# 剧本描述\n{script['description']}\n")

# 添加 planning 信息
if 'shared' in script and 'planning' in script['shared']:
    planning = script['shared']['planning']
    review_input.append(f"# 世界观设定\n{planning.get('worldview', '')}\n")
    
    review_input.append("# 角色设定\n")
    for char in planning.get('characters', []):
        review_input.append(f"- {char['name']}: {char.get('profile', '')}\n")
    
    review_input.append("\n# 剧情大纲\n")
    for outline in planning.get('outline', []):
        review_input.append(f"第{outline['chapter']}章 {outline.get('title', '')}: {outline['summary']}\n")

# 添加完整段落
review_input.append("\n# 剧本段落（完整）\n")
for seg in script['segments']:
    seg_id = seg.get('id', 'unknown')
    text = seg.get('text', '')
    if not text and 'display_break_lines' in seg:
        text = '\n'.join(seg['display_break_lines'])
    review_input.append(f"\n=== 段落 {seg_id} ===\n{text}\n")

# 保存为 .txt 文件
review_input_path = script_path.parent / "review_input.txt"
with open(review_input_path, "w", encoding="utf-8") as f:
    f.write('\n'.join(review_input))

print(f"剧本文本已保存至：{review_input_path}")
print(f"文件大小：{review_input_path.stat().st_size / 1024:.1f} KB")

# 后续调用 mcp_playwright-im_generate_text 时：
# context_files=["scripts/打倒群里的柚子厨/review_input.txt"]
EOF
```

## 相关文档

- DEVELOPMENT.md § 5：剧本数据约定
- PITFALLS.md § 4：生文 API 使用规范
