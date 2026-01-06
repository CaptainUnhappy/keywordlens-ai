---
name: amazon-keyword-filter
description: Filter Amazon keywords by product image similarity using AI vision analysis with MCP (zai-mcp-server). Searches Amazon, merges product images into grids, then uses MCP to analyze visual features (color, style, material, shape) for intelligent matching. Use for filtering keywords from Seller Sprite Excel files, analyzing product similarity with AI instead of perceptual hashing, batch processing keywords with semantic visual understanding, and reducing MCP calls by merging images (10+ calls becomes 2 calls per keyword).
---

# Amazon Keyword Filter (AI+MCP Mode)

Filter Amazon keywords using AI vision analysis via MCP for semantic understanding of product similarity.

## Setup

**使用 uv（推荐）**：

```bash
# 在你的工作目录
cd /path/to/your/project

# 安装 uv（如果还没有）
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 运行自动设置
python .claude/skills/amazon-keyword-filter/scripts/setup_env.py
```

**或手动设置**：

```bash
# 在你的工作目录创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install selenium pandas openpyxl pillow requests urllib3
```

**重要提示**：虚拟环境应该在你的**工作目录**创建，不是在skill文件夹内。

## Quick Start

### 单个关键词分析

```bash
python .claude/skills/amazon-keyword-filter/scripts/analyze_keyword_with_ai.py "wireless earbuds" my_product.jpg
```

Claude 会自动：
1. 搜索 Amazon 获取产品图片
2. 合并图片为网格
3. 调用 MCP 分析基准产品
4. 调用 MCP 分析合并网格
5. 计算加权相似度分数

### 批量关键词分析

```bash
python .claude/skills/amazon-keyword-filter/scripts/batch_analyze_with_ai.py keywords.xlsx my_product.jpg
```

处理 Excel 中所有关键词，共享基准产品分析。

## 核心脚本

**AI 分析**：
- `analyze_keyword_with_ai.py` - 单个关键词分析（MCP）
- `batch_analyze_with_ai.py` - 批量处理（共享基准分析）
- `auto_filter_with_ai.py` - 自动化关键词过滤工作流
- `generate_product_description.py` - AI 产品描述生成

**工具**：
- `search_amazon.py` - Amazon 搜索（支持截图）
- `merge_images.py` - 网格图片创建

**设置**：
- `setup_env.py` - 环境初始化

## 常用选项

```bash
# 自定义网格布局
python scripts/analyze_keyword_with_ai.py "test" product.jpg --columns 10

# 调试模式（显示浏览器）
python scripts/analyze_keyword_with_ai.py "test" product.jpg --debug --no-headless

# 自定义阈值
python scripts/analyze_keyword_with_ai.py "test" product.jpg --threshold 0.90

# 禁用 SSL 验证（修复下载错误）
python scripts/analyze_keyword_with_ai.py "test" product.jpg --no-ssl-verify
```

## MCP 集成

此 skill 需要访问 `zai-mcp-server__analyze_image`。Claude 运行分析脚本时会自动调用 MCP 工具。

**每个关键词的 MCP 调用次数**：
- 基准产品：1次（所有关键词共享）
- 每个关键词：1次（合并网格分析）
- 100个关键词总计：101次调用

## 输出结构

```
ai_analysis_results/
└── keyword_timestamp/
    ├── search_result.json      # Amazon 搜索结果
    ├── merged_grid.jpg         # MCP 网格图片
    └── analysis_result.json    # 最终分析结果
```

## 详细文档

需要更多信息？查看：
- **[AI Mode Guide](references/ai-mode.md)** - 完整 AI 工作流程和 MCP 调用详情
- **[Semantic Filtering Guide](references/semantic-filtering-guide.md)** - 语义过滤策略
- **[Configuration](references/configuration.md)** - 配置选项和自定义
- **[Troubleshooting](references/troubleshooting.md)** - 常见问题和解决方案
- **[API Reference](references/api_reference.md)** - 程序化使用文档

## 快速故障排查

**环境问题**：
```bash
# 检查虚拟环境
python -c "import sys; print('venv:', sys.prefix != sys.base_prefix)"

# 重新设置环境
python .claude/skills/amazon-keyword-filter/scripts/setup_env.py
```

**图片下载失败**：
```bash
python scripts/analyze_keyword_with_ai.py "test" product.jpg --no-ssl-verify
```

**想看浏览器运行**：
```bash
python scripts/analyze_keyword_with_ai.py "test" product.jpg --debug --no-headless
```

更多故障排查，参见 [troubleshooting.md](references/troubleshooting.md)。
