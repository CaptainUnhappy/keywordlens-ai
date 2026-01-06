# 智谱 AI 语义过滤完整指南

## 🎯 概述

使用智谱 AI Embedding-3 API 在搜索 Amazon 之前预先过滤关键词，节省 50-80% 的搜索时间。

**核心流程**:
```
产品图片 → MCP AI分析 → 产品描述 → 智谱Embedding → 关键词过滤 → Amazon搜索
```

---

## 📋 方案对比

### 方案 1: 全自动流程 ⭐ 推荐

**适用场景**: 在 Claude Code 环境中使用，完全自动化

**脚本**: `scripts/auto_filter_with_ai.py`

**流程**:
1. MCP AI 自动分析产品图片
2. 智谱 AI 自动过滤关键词
3. 输出过滤后的 Excel

**使用方法**:
```bash
# 在 Claude Code 中运行
python scripts/auto_filter_with_ai.py product.jpg keywords.xlsx --threshold 0.6

# 或直接提供产品描述
python scripts/auto_filter_with_ai.py \
    product.jpg keywords.xlsx \
    --description "Green shamrock headband for St Patrick's Day..." \
    --threshold 0.6
```

**优点**:
- ✅ 完全自动化
- ✅ 无需手动描述产品
- ✅ 一键完成所有步骤

**缺点**:
- ⚠️ 需要 Claude Code 环境
- ⚠️ 需要 MCP zai-mcp-server

---

### 方案 2: 手动描述流程

**适用场景**: 无 MCP 环境，或需要精确控制产品描述

**脚本**: `scripts/auto_filter_with_ai.py` (带 `--description` 参数)

**流程**:
1. 手动编写产品描述
2. 智谱 AI 自动过滤关键词
3. 输出过滤后的 Excel

**使用方法**:
```bash
# 直接在命令行提供描述
python scripts/auto_filter_with_ai.py \
    product.jpg keywords.xlsx \
    --description "Green shamrock headband for St. Patrick's Day parties. Features glittery shamrock decorations and green tinsel fringe. Suitable for kids and adults." \
    --threshold 0.6

# 或从 JSON 文件加载
python scripts/auto_filter_with_ai.py \
    product.jpg keywords.xlsx \
    --description-file product_description.json \
    --threshold 0.6
```

**优点**:
- ✅ 不依赖 MCP
- ✅ 可精确控制描述内容
- ✅ 可重复使用保存的描述

**缺点**:
- ⚠️ 需要手动编写描述
- ⚠️ 描述质量影响过滤效果

---

### 方案 3: 演示/测试流程

**适用场景**: 测试、演示、验证效果

**脚本**: `demo_zhipu_filter.py`

**流程**:
1. 在脚本中硬编码产品信息和关键词
2. 运行演示查看效果
3. 生成详细分析报告

**使用方法**:
```bash
# 直接运行（使用内置测试数据）
python demo_zhipu_filter.py

# 或修改脚本中的 PRODUCT_INFO 和 TEST_KEYWORDS
```

**优点**:
- ✅ 简单直接
- ✅ 适合快速验证
- ✅ 生成详细分析报告

**缺点**:
- ⚠️ 需要修改脚本
- ⚠️ 不适合批量处理

---

## 🚀 快速开始

### Step 1: 准备产品描述

#### 选项 A: 使用 MCP AI 自动生成（推荐）

在 Claude Code 中运行:

```python
# 让 Claude Code 调用 MCP 工具
"请使用 mcp__zai-mcp-server__analyze_image 分析我的产品图片 product.jpg，
生成用于语义关键词匹配的详细描述"
```

MCP 会返回类似这样的描述:

```
This is a green shamrock headband designed for St. Patrick's Day celebrations.
Features vibrant green color, glittery shamrock decorations, and tinsel fringe.
Made with flexible plastic band. Suitable for parties, parades, and Irish festivals.
Target audience: kids, teens, and adults. Related terms: headband, hair accessory,
St. Patrick's Day headband, shamrock headband, Irish headband, party accessory.
```

#### 选项 B: 手动编写产品描述

参考模板:

```
这是一个 [产品类别]，[主要颜色]，用于 [使用场合]。
特点: [材质], [设计元素], [独特特征]。
适合 [目标人群]。
相关搜索词: [关键词1], [关键词2], [关键词3]...
```

**示例**:
```
这是一个绿色三叶草头饰，用于圣帕特里克节派对。
特点: 塑料头箍，亮片三叶草装饰，绿色流苏。
适合儿童和成人。
相关搜索词: headband, shamrock, St Patrick's Day, green, party accessory.
```

---

### Step 2: 过滤关键词

准备好产品描述后，运行过滤:

```bash
# 使用自动化脚本
python scripts/auto_filter_with_ai.py \
    product.jpg \
    keywords.xlsx \
    --description "你的产品描述..." \
    --threshold 0.6
```

**参数说明**:
- `--threshold`: 相似度阈值
  - `0.8+`: 严格模式（只保留高度相关）
  - `0.6-0.8`: 平衡模式（推荐）
  - `0.4-0.6`: 宽松模式（广撒网）

---

### Step 3: 查看结果

脚本会生成两个文件:

1. **keywords_filtered.xlsx** - 过滤后的 Excel
   - 新增 "相似度得分" 列
   - 新增 "状态" 列 (✓ 通过 / ✗ 过滤)
   - 按得分降序排序

2. **keywords_filtered.json** - 详细结果
   ```json
   {
     "filtered_keywords": ["kw1", "kw2", ...],
     "all_scores": {"kw1": 0.85, "kw2": 0.78, ...},
     "stats": {
       "total": 100,
       "filtered": 40,
       "removed": 60,
       "filter_rate": 0.6,
       "avg_score": 0.65
     }
   }
   ```

---

## 📊 效果评估

### 阈值调整指南

根据首次运行结果调整:

| 现象 | 原因 | 解决方案 |
|------|------|---------|
| 通过率 < 10% | 阈值太严格 | 降低到 0.5-0.6 |
| 通过率 > 80% | 阈值太宽松 | 提高到 0.7-0.8 |
| 相关词被过滤 | 描述不完整 | 补充产品描述 |
| 不相关词通过 | 描述太宽泛 | 精简描述，聚焦核心特征 |

### 质量检查

查看 Top 10 和 Bottom 10 关键词:

```bash
# 查看结果
cat keywords_filtered.json | jq '.ranked_keywords[:10]'  # Top 10
cat keywords_filtered.json | jq '.ranked_keywords[-10:]' # Bottom 10
```

**预期效果**:
- ✅ Top 10 应该高度相关
- ✅ Bottom 10 应该明显不相关
- ✅ 阈值附近的关键词应该是"边缘案例"

---

## 💡 最佳实践

### 1. 产品描述撰写技巧

**✅ 好的描述**:
```
Green shamrock headband for St. Patrick's Day. Features glittery sequined
shamrocks and green tinsel fringe on flexible plastic band. Perfect for
Irish holiday parties, parades, and festivals. Suitable for women, kids,
and adults. Related items: headband, hair accessory, costume jewelry,
party decoration, Irish accessory, St. Paddy's Day headband.
```

**特点**:
- 包含产品类别 (headband)
- 描述关键特征 (shamrock, green, glittery)
- 说明用途 (St. Patrick's Day, parties)
- 列出目标人群 (women, kids, adults)
- 提供相关搜索词

**❌ 不好的描述**:
```
A nice green thing.
```

**问题**:
- 太简短
- 缺少关键信息
- 无法有效匹配关键词

---

### 2. 分阶段过滤策略

对于大量关键词（1000+），建议两阶段过滤:

**阶段 1: 宽松过滤 (threshold=0.4)**
```bash
python auto_filter_with_ai.py data.xlsx product.jpg --threshold 0.4
# 1000 → 400 关键词
```

**阶段 2: 严格过滤 (threshold=0.7)**
```bash
python auto_filter_with_ai.py data_filtered.xlsx product.jpg --threshold 0.7
# 400 → 100 关键词
```

**优势**:
- 第一阶段快速排除明显不相关的词
- 第二阶段精选高质量关键词
- 减少 API 调用（对已过滤的词不再处理）

---

### 3. 成本控制

#### 估算成本

```python
# 智谱 AI Embedding-3 定价: ¥0.5 / 百万 tokens
# 平均每个关键词 ~5 tokens
# 产品描述 ~50 tokens

关键词数量 = 100
tokens = 关键词数量 * 5 + 50 = 550
成本 = (550 / 1,000,000) * 0.5 = ¥0.000275 ≈ 0.03分

# 1000个关键词 ≈ ¥0.003 (0.3分)
# 10000个关键词 ≈ ¥0.03 (3分)
```

**结论**: 成本几乎可以忽略不计

---

## 🔧 集成到主流程

### 修改 batch_analyze_with_ai.py

在主流程中添加预过滤阶段:

```python
# Stage 0: 加载配置
config = load_config()

# Stage 1: 分析基准产品
reference_analysis = analyze_reference_product(reference_image)

# ✨ NEW: Stage 1.5: 语义预过滤
if config.get("enable_semantic_filter", False):
    print("\n🔍 Stage 1.5: 智谱 AI 语义预过滤...")

    from scripts.auto_filter_with_ai import filter_keywords_with_zhipu

    # 生成产品描述
    product_desc = reference_analysis.get("description", "")

    # 过滤关键词
    filter_result = filter_keywords_with_zhipu(
        keywords=keywords,
        product_description=product_desc,
        threshold=config.get("semantic_threshold", 0.6)
    )

    # 使用过滤后的关键词
    keywords = filter_result["filtered_keywords"]

    print(f"   ✓ 过滤前: {filter_result['stats']['total']} 个关键词")
    print(f"   ✓ 过滤后: {filter_result['stats']['filtered']} 个关键词")
    print(f"   ✓ 节省搜索: {filter_result['stats']['filter_rate']:.1%}")

# Stage 2: 搜索 Amazon (只搜索过滤后的关键词)
for keyword in keywords:
    search_amazon(keyword)
    ...
```

### 配置文件更新

在 `config.json` 中添加:

```json
{
  "enable_semantic_filter": true,
  "semantic_threshold": 0.6,
  "zhipu_api_key": "your-api-key-here",
  "embedding_dimensions": 1024
}
```

---

## 📈 性能对比

### 完整流程时间对比

| 阶段 | 无语义过滤 | 有语义过滤 | 节省 |
|------|----------|-----------|------|
| 关键词数 | 100 | 100 → 40 | - |
| 语义过滤 | - | 3秒 | +3秒 |
| Amazon搜索 | 100 × 8秒 = 13分钟 | 40 × 8秒 = 5分钟 | **-8分钟** |
| 图片分析 | 100 × 5秒 = 8分钟 | 40 × 5秒 = 3分钟 | **-5分钟** |
| **总计** | **21分钟** | **8分钟** | **-13分钟 (62%)** |

### ROI 分析

```
时间节省: 13分钟
API成本: ¥0.0003 (100个关键词)
人工时薪: ¥100/小时

节省价值 = (13/60) × 100 = ¥21.67
成本 = ¥0.0003
ROI = 21.67 / 0.0003 ≈ 72,233倍 ⭐⭐⭐⭐⭐
```

---

## 🐛 常见问题

### Q1: 相关关键词被过滤了怎么办？

**原因**: 产品描述不完整或阈值太高

**解决**:
1. 检查被过滤的关键词
2. 补充产品描述中缺失的特征
3. 或降低阈值 (e.g., 0.7 → 0.6)

---

### Q2: 不相关关键词通过了怎么办？

**原因**: 产品描述太宽泛或阈值太低

**解决**:
1. 精简产品描述，聚焦核心特征
2. 移除过于泛化的词汇
3. 或提高阈值 (e.g., 0.5 → 0.6)

---

### Q3: MCP 分析的描述太简单？

**解决**: 在 MCP 提示词中要求更详细的分析

```python
prompt = """
请详细分析这个产品，包括:
1. 精确的颜色描述 (不要只说"绿色"，要说"鲜艳的绿色"或"深绿色")
2. 所有可见的材质和纹理
3. 设计细节和装饰元素
4. 可能的使用场景和目标人群
5. 至少20个相关搜索词
"""
```

---

### Q4: API 调用失败？

**检查**:
1. API Key 是否正确
2. 网络连接是否正常
3. 是否达到 API 限流

**解决**:
```bash
# 测试 API 连接
curl -X POST https://open.bigmodel.cn/api/paas/v4/embeddings \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"embedding-3","input":["test"],"dimensions":1024}'
```

---

## 📚 参考资源

- **智谱 AI Embedding-3 文档**: https://open.bigmodel.cn/dev/api#embedding
- **MCP zai-mcp-server**: 图片分析工具
- **Demo 脚本**: `demo_zhipu_filter.py`
- **自动化脚本**: `scripts/auto_filter_with_ai.py`

---

## ✅ 总结

### 核心优势

1. ✅ **大幅节省时间**: 减少 50-80% 的 Amazon 搜索
2. ✅ **成本极低**: 1000 个关键词仅需 ¥0.003
3. ✅ **高度准确**: 语义理解优于简单的文本匹配
4. ✅ **易于集成**: 可无缝集成到现有流程

### 推荐工作流程

```
1. 准备产品图片和关键词 Excel
2. 使用 MCP AI 分析图片生成描述 (或手动编写)
3. 运行语义过滤脚本
4. 检查过滤结果，调整阈值
5. 使用过滤后的关键词进行 Amazon 搜索
6. 进行图片相似度比对
```

---

**更新日期**: 2026-01-05
**版本**: v1.0
**维护**: Amazon Keyword Filter Skill
