# Phase 2 架构优化 - 实施计划

## 目标
基于Phase 1质量门禁基础，建立角色外观一致性机制，并增强分镜级质量控制精度。

---

## Phase 1 验证结果回顾

### ✅ 已解决
- 重复段落检测：100%检出率
- 前置重复检测：重复段落从4个降至1个（-75%）
- Segment ID稳定性：94.6%
- 质量门禁阈值：50%旁白阈值生效

### ⚠️ 待解决
1. **角色外观一致性缺失**：无三视图基准，立绘生成使用文生图（无参考图）
2. **分镜级旁白算法不精准**：storyboards[1]旁白45%，3轮修复后仍未达标
3. **风格锚点混乱**：所有角色共享通用风格，无按角色分类
4. **1个重复段落残留**：候选池质量问题（小说开头场景被过度复用）

---

## Phase 2 核心任务

### 2.1 三视图生成机制（优先级：高）

**目标**: 为每个角色生成三视图设定（front/left/right），建立外观基准

**新增文件**: `engine/character_design_generator.py`

**核心功能**:
```python
def generate_three_view_design(
    character_name: str,
    character_desc: str,
    style_anchor: str,
    script_name: str
) -> str:
    """生成角色三视图设定（front/left/right）

    Returns:
        三视图合成图路径: assets/char_ref_{character_name}_three_view.png
    """
    views = ["正面", "左侧面", "右侧面"]
    view_paths = []

    for view in views:
        prompt = (
            f"{character_desc}, "
            f"{view}视角, "
            f"角色设定单, 三视图, "
            f"{style_anchor}, "
            f"clean lineart, character turnaround sheet"
        )

        negative = "背景, 多角色, 文字, 水印, 低质量, 模糊"

        result = generate_image(
            script_name=script_name,
            prompt=prompt,
            negative_prompt=negative,
            filename=f"char_ref_{character_name}_{view}.png",
            width=1280,
            height=720,  # 横版，用于设定图
            api_action="TextToImageLite"
        )
        view_paths.append(result)

    # 合成为单张三视图
    composite_path = f"assets/char_ref_{character_name}_three_view.png"
    _composite_three_views(view_paths, composite_path)

    return composite_path
```

**集成点**:
- 模块3开始前，调用 `generate_three_view_design()` 为每个角色生成三视图
- 三视图路径写入 `shared.character_refs[角色名].three_view_ref`

**验收标准**:
- 每个角色生成1张三视图（包含front/left/right三个视角）
- 三视图存储到 `scripts/{script_name}/assets/char_ref_{角色名}_three_view.png`
- 不直接绑定到 `character_image`（立绘由图生图生成）

---

### 2.2 图生图立绘一致性（优先级：高）

**目标**: 所有角色立绘必须基于三视图使用图生图生成

**修改文件**: `.claude/skills/generate-scene-assets/SKILL.md`

**强制流程**:
```markdown
## 角色立绘生成流程（强制）

### 前置条件检查
1. 检查 `assets/char_ref_{角色名}_three_view.png` 是否存在
2. 若不存在，先调用 `character_design_generator.generate_three_view_design()`

### 立绘生成（必须使用图生图）
- **API**: `SubmitTextToImageJob`（禁止使用 TextToImageLite）
- **reference_images**: `[scripts/{script_name}/assets/char_ref_{角色名}_three_view.png]`
- **分辨率**: `720x1280`（竖版，用于游戏显示）
- **提示词**: `{角色名}, {表情状态}, 半身构图, 竖版立绘, {style_anchor}`
- **负向提示词**: `背景, 环境, 多角色, 全身, 横版, 低质量`

### 生成状态清单
- default（默认/平静）
- angry（愤怒）
- sad（悲伤）
- happy（高兴）
- surprised（惊讶）

### 资产绑定
- `character_image` 必须绑定竖版立绘，禁止直接使用三视图
- 示例：`"character_image": "assets/char_沈砚_default.png"`
```

**验收标准**:
- 立绘生成100%使用图生图路径
- 每个角色至少生成1个状态立绘（default）
- 立绘为竖版（720x1280）
- 立绘视觉风格与三视图保持一致

---

### 2.3 风格合同按角色分类（优先级：中）

**目标**: 每个角色独立维护风格锚点，避免风格混乱

**修改文件**:
- `scripts/*/assets/_style_contract.json`（数据结构）
- `.mcp/hunyuan_backend.py`（更新逻辑）

**新结构**:
```json
{
  "global_style_anchor": "anime visual novel, clean lineart, soft lighting, consistent color grading",
  "global_negative_anchor": "低质量, 模糊, 水印, 文本, logo, 畸形",

  "character_styles": {
    "沈砚": {
      "style_anchor": "男性, 30岁, 风衣, 忧郁气质, 深色调",
      "negative_anchor": "笑容, 明亮色调, 西装",
      "three_view_ref": "assets/char_ref_沈砚_three_view.png",
      "portraits": {
        "default": "assets/char_沈砚_default.png",
        "angry": "assets/char_沈砚_angry.png"
      }
    },
    "顾行舟": {
      "style_anchor": "女性, 28岁, 制服, 锐利目光, 冷峻",
      "negative_anchor": "柔和, 甜美, 休闲装",
      "three_view_ref": "assets/char_ref_顾行舟_three_view.png",
      "portraits": {
        "default": "assets/char_顾行舟_default.png"
      }
    }
  },

  "background_style_anchor": "realistic environment, cinematic composition, moody lighting",
  "background_negative_anchor": "人物, 人影, 路人, 角色, 文字",

  "updated_at": "2026-03-12T15:00:00"
}
```

**代码修改**: `.mcp/hunyuan_backend.py`
```python
def _update_style_contract(
    style_contract: dict,
    scene_type: str,
    character_name: str | None,  # 新增参数
    style_anchor: str,
    negative_anchor: str
) -> None:
    """更新风格合同，支持按角色分类"""
    if scene_type == "background":
        style_contract["background_style_anchor"] = style_anchor
        style_contract["background_negative_anchor"] = negative_anchor
    elif scene_type == "character" and character_name:
        # 按角色分类存储
        if "character_styles" not in style_contract:
            style_contract["character_styles"] = {}
        if character_name not in style_contract["character_styles"]:
            style_contract["character_styles"][character_name] = {}

        style_contract["character_styles"][character_name]["style_anchor"] = style_anchor
        style_contract["character_styles"][character_name]["negative_anchor"] = negative_anchor

    style_contract["updated_at"] = datetime.now().isoformat()
```

**验收标准**:
- 每个角色独立存储 `style_anchor` 和 `negative_anchor`
- 三视图路径记录到 `three_view_ref`
- 已生成立绘路径记录到 `portraits[状态]`

---

### 2.4 分镜级旁白补入算法（优先级：中）

**目标**: 精准计算每个分镜需要补充的旁白数，解决分镜级旁白不达标问题

**修改文件**: `engine/script_quality.py`

**当前问题**:
```python
# Phase 1逻辑（全局算法）
for sb in storyboards:
    narr = sum(1 for s in scripts if s["speaker"] == "旁白")
    total = len(scripts)
    need = _required_insertions(total, narr, target_ratio)  # 全局计算
    # 若need<=0则跳过该分镜
```

**改进方案**:
```python
# Phase 2逻辑（分镜级算法）
def enrich_narration_with_novel(
    data: dict[str, Any],
    novel_text: str,
    target_ratio: float = 0.50,
) -> dict[str, Any]:
    result = copy.deepcopy(data)
    candidates = _extract_narration_candidates(novel_text)
    existing_texts = _collect_existing_texts(result)

    for sb_idx, sb in enumerate(result.get("storyboards", [])):
        scripts = sb.get("scripts", [])
        if not scripts:
            continue

        # 【修改】分镜级计算
        sb_total = len(scripts)
        sb_narr = sum(1 for s in scripts if s.get("speaker") == NARRATION_SPEAKER)
        sb_need = _required_insertions(sb_total, sb_narr, target_ratio)

        if sb_need <= 0:
            continue  # 该分镜已达标

        # 为该分镜精准插入 sb_need 个旁白
        inserted = 0
        for pos_idx in _calculate_insertion_positions(scripts, sb_need):
            candidate = _get_next_valid_candidate(candidates, existing_texts)
            if not candidate:
                break  # 候选池耗尽

            scripts.insert(pos_idx + inserted, {
                "id": "",
                "speaker": NARRATION_SPEAKER,
                "text": candidate,
                "character_image": None,
                "effect": "typewriter",
                "speed": 55
            })
            existing_texts.append(candidate)
            inserted += 1

        # 确保分镜以旁白开头
        if scripts[0].get("speaker") != NARRATION_SPEAKER:
            first_narration = _get_next_valid_candidate(candidates, existing_texts)
            if first_narration:
                scripts.insert(0, {
                    "id": "",
                    "speaker": NARRATION_SPEAKER,
                    "text": first_narration,
                    ...
                })

    return result
```

**验收标准**:
- 每个分镜旁白占比≥50%（全局+分镜级双达标）
- storyboards[1]从45%提升至≥50%
- 不引入新的重复段落

---

### 2.5 候选池质量增强（优先级：低，可选）

**目标**: 解决小说开头场景过度复用问题

**方案1: 主题感知筛选**（推荐）
```python
def _filter_candidates_by_theme(
    candidates: deque[str],
    storyboard_title: str
) -> deque[str]:
    """根据分镜主题筛选相关旁白候选"""
    if not storyboard_title:
        return candidates

    # 提取主题关键词（如"雨夜回访" → ["雨", "夜", "回访"]）
    keywords = _extract_keywords(storyboard_title)

    # 优先返回包含关键词的候选
    relevant = deque()
    others = deque()

    for text in candidates:
        if any(kw in text for kw in keywords):
            relevant.append(text)
        else:
            others.append(text)

    # 相关候选 + 其他候选（兜底）
    relevant.extend(others)
    return relevant
```

**方案2: 使用频率限制**（备选）
```python
# 记录每个候选被使用的次数，超过2次则跳过
candidate_usage = {}

def _get_next_valid_candidate(candidates, existing_texts, max_reuse=1):
    for _ in range(len(candidates)):
        candidate = candidates[0]
        candidates.rotate(-1)

        # 检查重复
        if any(_calculate_similarity(candidate, t) >= 0.85 for t in existing_texts):
            continue

        # 检查使用频率
        usage_count = candidate_usage.get(candidate, 0)
        if usage_count >= max_reuse:
            continue

        candidate_usage[candidate] = usage_count + 1
        return candidate

    return None
```

**验收标准**:
- 残留的1个重复段落被消除
- 各分镜旁白内容与分镜主题相关

---

## Phase 2 实施顺序

### Week 1-2: 角色一致性机制

**Day 1-2**:
- 创建 `engine/character_design_generator.py`
- 实现 `generate_three_view_design()` 函数
- 实现 `_composite_three_views()` 图片合成

**Day 3-4**:
- 修改 `.claude/skills/generate-scene-assets/SKILL.md`
- 更新立绘生成流程为强制图生图
- 添加前置条件检查逻辑

**Day 5-7**:
- 升级 `_style_contract.json` 数据结构
- 修改 `.mcp/hunyuan_backend.py` 的 `_update_style_contract()`
- 测试风格合同按角色分类功能

**验收**: 在测试剧本上生成三视图 + 图生图立绘，验证外观一致性

---

### Week 3: 分镜级算法增强

**Day 1-2**:
- 重构 `enrich_narration_with_novel()` 为分镜级计算
- 添加 `_calculate_insertion_positions()` 辅助函数
- 添加 `_get_next_valid_candidate()` 辅助函数

**Day 3-4**:
- （可选）实现主题感知候选筛选
- 测试分镜级旁白补入效果

**Day 5**:
- 在渡口回灯上完整回归测试
- 验证 storyboards[1] 旁白占比是否≥50%

**验收**: 所有分镜旁白占比≥50%，无新增重复段落

---

## 预期效果

### 主要指标

| 指标 | Phase 1 | Phase 2目标 | 改进幅度 |
|------|---------|-------------|----------|
| 角色一致性得分 | N/A | ≥85% | 新建 |
| 分镜级旁白达标率 | 60% | ≥95% | +58% |
| 背景图人物出现率 | ~20% | <5% | -75% |
| 残留重复段落 | 1个 | 0个 | -100% |

### 次要指标

- 立绘图生图使用率：100%
- 风格合同分类覆盖率：100%角色
- 三视图生成成功率：≥90%

---

## 风险评估

### 高风险项

**1. 三视图合成技术复杂度**
- 风险：三视图合成可能需要外部库（如PIL、OpenCV）
- 缓解：
  - Phase 2.1先实现单视图生成，合成功能作为增强项
  - 可使用简单拼接代替复杂合成

**2. 图生图API稳定性**
- 风险：混元图生图接口可能有限流或任务超时
- 缓解：
  - 参考 Phase 1.5 的重试机制
  - 添加降级策略：图生图失败时回退到文生图+style_anchor

### 中风险项

**3. 风格合同结构升级可能破坏兼容性**
- 风险：旧剧本的 `_style_contract.json` 结构不兼容
- 缓解：
  - 添加迁移逻辑：自动将旧格式转换为新格式
  - 保留全局 `style_anchor` 作为兜底

**4. 分镜级算法可能引入新的边界问题**
- 风险：候选池耗尽时某些分镜仍未达标
- 缓解：
  - 添加候选池容量检查，提前警告
  - 保留全局补入作为兜底

---

## 回退计划

**如果Phase 2效果不佳**:
1. 三视图机制：禁用，回退到纯文生图
2. 图生图强制：降级为"推荐使用"，允许文生图
3. 风格合同分类：保留全局格式，按需启用角色分类
4. 分镜级算法：回退到Phase 1.5+的全局算法

**回退触发条件**:
- 角色一致性得分<60%
- 图生图失败率>30%
- 分镜级算法引入重复段落≥2个

---

## 下一步行动

### 立即开始
1. 创建 `engine/character_design_generator.py`
2. 实现三视图生成函数（不含合成，先验证单视图）
3. 在测试剧本上试运行

### Phase 2完成后
1. 编写 `docs/PHASE2_SUMMARY.md`
2. 编写 `docs/PHASE2_VALIDATION.md`
3. 决定是否进入Phase 3（增量改写、智能批次、统一停止条件）

---

**Phase 2预计耗时**: 2-3周
**Phase 2成功标准**: 角色一致性≥85%，分镜级旁白达标率≥95%
