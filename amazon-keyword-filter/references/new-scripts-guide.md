# 新增脚本使用指南

本文档介绍最近添加的新脚本及其使用方法。

## auto_filter_with_ai.py

### 功能

自动化关键词过滤流程，结合两种 AI 技术：
1. **MCP AI 视觉分析** - 分析产品图片生成详细描述
2. **智谱 AI Embedding** - 使用语义相似度过滤关键词

### 使用场景

当你有一个产品图片和一个大量关键词列表，需要快速筛选出语义上相关的关键词时使用。

### 基本用法

```bash
python .claude/skills/amazon-keyword-filter/scripts/auto_filter_with_ai.py product.jpg keywords.xlsx
```

### 参数说明

```bash
python auto_filter_with_ai.py <product_image> <keywords_excel> [options]

必需参数:
  product_image        产品图片路径 (JPG/PNG)
  keywords_excel       关键词Excel文件路径

可选参数:
  --threshold FLOAT    相似度阈值 (默认: 0.6)
                      值越高，过滤越严格
  --column NAME        Excel中关键词列名 (默认: "关键词")
  -o, --output FILE    输出文件路径 (默认: filtered_keywords.json)
```

### 示例

```bash
# 基本用法
python scripts/auto_filter_with_ai.py my_product.jpg keywords.xlsx

# 自定义阈值（更严格的过滤）
python scripts/auto_filter_with_ai.py my_product.jpg keywords.xlsx --threshold 0.7

# 指定关键词列名
python scripts/auto_filter_with_ai.py my_product.jpg keywords.xlsx --column "Search Terms"

# 自定义输出文件
python scripts/auto_filter_with_ai.py my_product.jpg keywords.xlsx -o results/filtered.json
```

### 工作流程

1. **MCP 分析产品图片**
   - 调用 `zai-mcp-server__analyze_image`
   - 生成详细的产品描述
   - 包括：类别、视觉特征、用途、风格等

2. **获取产品描述 Embedding**
   - 使用智谱 AI Embedding API
   - 将产品描述转换为 1024 维向量

3. **批量处理关键词**
   - 读取 Excel 文件中的所有关键词
   - 为每个关键词生成 Embedding
   - 计算与产品描述的余弦相似度

4. **过滤和排序**
   - 筛选出相似度 >= 阈值的关键词
   - 按相似度从高到低排序
   - 保存结果到 JSON 文件

### 输出格式

```json
{
  "product_image": "my_product.jpg",
  "product_description": "详细的产品描述...",
  "total_keywords": 100,
  "filtered_count": 25,
  "threshold": 0.6,
  "results": [
    {
      "keyword": "christmas headband",
      "similarity": 0.85,
      "rank": 1
    },
    {
      "keyword": "festive hair accessories",
      "similarity": 0.78,
      "rank": 2
    }
  ]
}
```

### 配置要求

**环境变量或配置文件**：
- `ZHIPU_API_KEY` - 智谱 AI API 密钥
- 或在脚本中直接配置（不推荐用于生产环境）

**注意**：当前版本脚本中包含硬编码的 API 密钥，建议改为环境变量：

```bash
# Windows
set ZHIPU_API_KEY=your_api_key_here

# Linux/Mac
export ZHIPU_API_KEY=your_api_key_here
```

### 性能考虑

- **MCP 调用**：1次（分析产品图片）
- **Embedding API 调用**：N+1 次（1次产品描述 + N个关键词）
- **处理速度**：约 5-10 秒/100个关键词
- **成本**：主要取决于智谱 AI Embedding API 费用

---

## generate_product_description.py

### 功能

专门用于生成产品描述的独立脚本。使用 MCP AI 视觉分析生成优化的产品描述，可用于：
- 语义关键词过滤
- SEO 优化
- 产品文案生成

### 基本用法

```bash
python .claude/skills/amazon-keyword-filter/scripts/generate_product_description.py product.jpg
```

### 参数说明

```bash
python generate_product_description.py <product_image> [options]

必需参数:
  product_image        产品图片路径

可选参数:
  -o, --output FILE    输出文件路径 (默认: product_description.json)
  --format FORMAT      输出格式: json|text (默认: json)
```

### 示例

```bash
# 基本用法
python scripts/generate_product_description.py my_product.jpg

# 自定义输出路径
python scripts/generate_product_description.py my_product.jpg -o descriptions/product_001.json

# 纯文本格式输出
python scripts/generate_product_description.py my_product.jpg --format text
```

### MCP 提示词模板

脚本使用精心设计的提示词来引导 AI 生成结构化描述：

1. **Product Category** - 产品类别
2. **Visual Features** - 视觉特征（颜色、材质、形状）
3. **Purpose/Use Case** - 用途和使用场景
4. **Style/Theme** - 风格主题
5. **Key Distinguishing Features** - 关键特征
6. **Related Search Terms** - 相关搜索词

### 输出格式

**JSON 格式**（默认）：
```json
{
  "product_image": "my_product.jpg",
  "timestamp": "2026-01-05T10:30:00",
  "description": {
    "category": "Headband",
    "visual_features": {
      "colors": ["vibrant green", "red"],
      "materials": ["fabric", "sequins"],
      "shape": "bow-shaped decoration"
    },
    "purpose": "Holiday party accessory",
    "style": "Festive, playful",
    "distinguishing_features": [
      "Large bow design",
      "Sequin decoration",
      "Christmas theme"
    ],
    "search_terms": [
      "christmas headband",
      "festive bow",
      "holiday hair accessory"
    ]
  },
  "full_description": "完整的流畅描述文本..."
}
```

**Text 格式**：
```
Product Analysis: my_product.jpg

Category: Headband

Visual Features:
- Colors: vibrant green, red
- Materials: fabric, sequins
- Shape: bow-shaped decoration

[... 其余部分 ...]

Full Description:
This is a festive headband featuring...
```

### 与其他脚本配合使用

**配合 auto_filter_with_ai.py**：
```bash
# 1. 生成产品描述
python scripts/generate_product_description.py product.jpg -o temp/description.json

# 2. 使用描述进行关键词过滤
python scripts/auto_filter_with_ai.py product.jpg keywords.xlsx
```

**配合批量分析**：
```bash
# 为多个产品生成描述
for img in products/*.jpg; do
    python scripts/generate_product_description.py "$img" -o "descriptions/$(basename $img .jpg).json"
done
```

### 高级用法

**自定义 MCP 提示词**：

编辑脚本中的 `PRODUCT_ANALYSIS_PROMPT` 变量来自定义分析重点。例如，针对服装产品：

```python
PRODUCT_ANALYSIS_PROMPT = """Analyze this clothing item...

Focus on:
1. Garment type and fit
2. Fabric and texture
3. Season and occasion
4. Fashion style
5. Target demographic
...
"""
```

### 依赖要求

- **Claude Code CLI** - 用于 MCP 访问
- **zai-mcp-server** - 图片分析工具
- Python 3.8+
- 标准库（无额外依赖）

### 故障排查

**MCP 工具不可用**：
```
Error: zai-mcp-server__analyze_image not available
```
解决：确保在 Claude Code 环境中运行，或检查 MCP 服务器配置。

**图片格式不支持**：
```
Error: Unsupported image format
```
解决：使用 JPG、PNG 或其他常见格式。必要时转换格式：
```bash
convert image.webp image.jpg
```

---

## 集成使用示例

### 完整工作流

```bash
# 1. 生成产品描述
python scripts/generate_product_description.py product.jpg

# 2. 使用描述自动过滤关键词
python scripts/auto_filter_with_ai.py product.jpg keywords.xlsx --threshold 0.65

# 3. 对过滤后的关键词进行Amazon分析
python scripts/batch_analyze_with_ai.py filtered_keywords.json product.jpg
```

### 批量处理多个产品

```bash
#!/bin/bash
# batch_process.sh

PRODUCTS_DIR="products"
KEYWORDS_FILE="all_keywords.xlsx"
OUTPUT_DIR="results"

for product in $PRODUCTS_DIR/*.jpg; do
    product_name=$(basename "$product" .jpg)

    echo "Processing: $product_name"

    # 生成描述
    python scripts/generate_product_description.py "$product" \
        -o "$OUTPUT_DIR/${product_name}_description.json"

    # 过滤关键词
    python scripts/auto_filter_with_ai.py "$product" "$KEYWORDS_FILE" \
        --threshold 0.65 \
        -o "$OUTPUT_DIR/${product_name}_keywords.json"

    echo "Completed: $product_name"
done
```

---

## 最佳实践

1. **先测试单个产品**
   - 用少量关键词测试阈值设置
   - 验证过滤结果质量

2. **调整相似度阈值**
   - 0.5-0.6：宽松，包含更多关键词
   - 0.6-0.7：平衡，推荐用于大多数场景
   - 0.7-0.8：严格，只保留高度相关的关键词

3. **监控 API 成本**
   - 记录 API 调用次数
   - 批量处理时考虑速率限制

4. **保存中间结果**
   - 产品描述可重用
   - 避免重复的 MCP 调用

5. **验证过滤结果**
   - 人工抽查高相似度和低相似度的关键词
   - 根据实际效果调整阈值
