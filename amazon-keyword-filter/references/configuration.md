# 配置指南

## 环境配置

### 虚拟环境

**必需：使用 uv 管理虚拟环境**

```bash
# 安装 uv
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境（在工作目录，不是 skill 目录）
cd /path/to/your/project
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
uv pip install selenium pandas openpyxl pillow requests urllib3
```

### 环境变量

可选环境变量配置：

```bash
# Amazon 配置
export AMAZON_DOMAIN="amazon.com"           # 默认：amazon.com
export MAX_PRODUCTS=20                       # 每个关键词最多获取产品数

# 智谱 AI（用于 auto_filter_with_ai.py）
export ZHIPU_API_KEY="your_api_key_here"    # 智谱 AI Embedding API 密钥

# Selenium 配置
export SELENIUM_HEADLESS=true                # 是否使用无头模式
export SELENIUM_TIMEOUT=30                   # 超时时间（秒）

# 输出配置
export OUTPUT_DIR="./results"                # 默认输出目录
export DEBUG_MODE=false                      # 调试模式
```

**Windows 设置环境变量**：
```powershell
$env:AMAZON_DOMAIN="amazon.com"
$env:ZHIPU_API_KEY="your_api_key"
```

**永久设置（添加到 .bashrc / .zshrc）**：
```bash
echo 'export ZHIPU_API_KEY="your_api_key"' >> ~/.bashrc
source ~/.bashrc
```

## config.json 配置文件

### 基础结构

```json
{
  "product_image": "my_product.jpg",
  "excel_file": "seller_sprite_keywords.xlsx",
  "keyword_column": "关键词",
  "output_file": "filtered_keywords.xlsx",
  "similarity_threshold": 0.85,
  "min_matches": 2,
  "amazon_domain": "amazon.com",
  "max_products": 20,
  "grid_columns": 5,
  "concurrent_workers": 5
}
```

### 参数详解

#### product_image
- **类型**: string
- **说明**: 基准产品图片路径
- **示例**: `"my_product.jpg"` 或 `"products/headphones.png"`
- **要求**:
  - 支持格式: JPG, PNG, WEBP
  - 建议使用清晰的产品主图（白底、正面）
  - 文件大小 < 10MB

#### excel_file
- **类型**: string
- **说明**: 卖家精灵下载的关键词 Excel 文件
- **示例**: `"seller_sprite_keywords.xlsx"`
- **要求**:
  - 格式: .xlsx, .xls, .csv
  - 必须包含关键词列

#### keyword_column
- **类型**: string
- **默认**: `"关键词"`
- **说明**: Excel 中关键词所在列的列名
- **示例**: `"Keyword"`, `"关键词"`, `"搜索词"`

#### similarity_threshold
- **类型**: float
- **范围**: 0.0 - 1.0
- **默认**: 0.85
- **说明**: 相似度阈值，只有达到此阈值才算匹配
- **调优建议**:
  ```
  0.50-0.60: 非常宽松，用于初步筛选
  0.60-0.70: 宽松筛选，包含更多相似产品
  0.75-0.80: 平衡模式
  0.85:      默认推荐，平衡准确度和覆盖率
  0.90-0.95: 严格筛选，只保留高度相似产品
  0.95+:     极度严格，几乎完全一致
  ```

#### min_matches
- **类型**: integer
- **默认**: 2
- **说明**: 关键词至少需要多少个匹配产品才算合格
- **示例**:
  - `2`: 至少2个产品相似度 >= threshold
  - `5`: 至少5个产品相似度 >= threshold

#### amazon_domain
- **类型**: string
- **默认**: `"amazon.com"`
- **说明**: Amazon 站点域名
- **可选值**:
  - `"amazon.com"` - 美国站
  - `"amazon.co.uk"` - 英国站
  - `"amazon.de"` - 德国站
  - `"amazon.fr"` - 法国站
  - `"amazon.co.jp"` - 日本站
  - `"amazon.ca"` - 加拿大站

#### max_products
- **类型**: integer
- **默认**: 20
- **范围**: 1-50
- **说明**: 每个关键词最多获取多少个产品
- **建议**:
  - 10-15: 快速分析
  - 20: 平衡（推荐）
  - 30-50: 全面分析（耗时更长）

#### grid_columns
- **类型**: integer
- **默认**: 5
- **范围**: 2-10
- **说明**: 合并图片网格的列数
- **影响**:
  - 较少列（2-3）：图片更大，细节清晰
  - 较多列（8-10）：图片更小，整体布局紧凑
  - 推荐 5 列：平衡大小和布局

#### concurrent_workers
- **类型**: integer
- **默认**: 5
- **范围**: 1-10
- **说明**: 批量处理时的并发线程数
- **建议**:
  - 1-3: 低性能机器
  - 5: 推荐（平衡速度和稳定性）
  - 8-10: 高性能机器

## MCP 配置

### 必需的 MCP 工具

此 skill 依赖以下 MCP 工具：

1. **zai-mcp-server__analyze_image**
   - 用途：图片视觉分析
   - 提供者：zai-mcp-server
   - 配置：在 Claude Code 设置中启用

### MCP 权限配置

在 `.claude/settings.json` 或 `.claude/settings.local.json` 中配置：

```json
{
  "mcpServers": {
    "zai-mcp-server": {
      "command": "npx",
      "args": ["-y", "@anthropic/zai-mcp-server"],
      "autoApprove": [
        "analyze_image"
      ]
    }
  },
  "permissions": {
    "zai-mcp-server__analyze_image": "allow"
  }
}
```

### MCP 调用配置

配置 MCP 调用参数：

```json
{
  "mcp_config": {
    "max_retries": 3,
    "timeout": 60,
    "batch_size": 10
  }
}
```

## 命令行参数

### analyze_keyword_with_ai.py

```bash
python scripts/analyze_keyword_with_ai.py [OPTIONS] KEYWORD PRODUCT_IMAGE

参数:
  KEYWORD              搜索关键词
  PRODUCT_IMAGE        基准产品图片

选项:
  --amazon-domain      Amazon 域名 (默认: amazon.com)
  --max-products N     最多获取商品数 (默认: 20)
  --columns N          网格列数 (默认: 5)
  --threshold FLOAT    相似度阈值 (默认: 0.85)
  -o, --output DIR     输出目录
  --debug              调试模式
  --no-headless        显示浏览器窗口
  --no-ssl-verify      禁用 SSL 验证
```

### batch_analyze_with_ai.py

```bash
python scripts/batch_analyze_with_ai.py [OPTIONS] EXCEL_FILE PRODUCT_IMAGE

参数:
  EXCEL_FILE           Excel 文件路径
  PRODUCT_IMAGE        基准产品图片

选项:
  --column NAME        关键词列名 (默认: 关键词)
  --amazon-domain      Amazon 域名
  --max-products N     最多获取商品数
  --columns N          网格列数
  --threshold FLOAT    相似度阈值
  -o, --output DIR     输出目录
  --cache FILE         进度缓存文件
  --workers N          并发工作线程数 (默认: 5)
  --no-filter          禁用 AI 关键词过滤
  --debug              调试模式
  --no-headless        显示浏览器窗口
  --no-ssl-verify      禁用 SSL 验证
```

### auto_filter_with_ai.py

```bash
python scripts/auto_filter_with_ai.py [OPTIONS] PRODUCT_IMAGE EXCEL_FILE

参数:
  PRODUCT_IMAGE        产品图片路径
  EXCEL_FILE           关键词 Excel 文件

选项:
  --threshold FLOAT    相似度阈值 (默认: 0.6)
  --column NAME        关键词列名
  -o, --output FILE    输出文件路径
```

## 高级配置

### ChromeDriver 配置

如果需要自定义 ChromeDriver 路径或选项：

```python
# 在 search_amazon.py 中修改
chrome_options.add_argument('--user-data-dir=/path/to/profile')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
```

### 代理配置

```python
# 添加代理支持
chrome_options.add_argument('--proxy-server=http://proxy.example.com:8080')
```

### 超时配置

```python
# 修改 Selenium 超时
driver.implicitly_wait(10)  # 隐式等待 10 秒
driver.set_page_load_timeout(30)  # 页面加载超时 30 秒
```

## 配置模板

### 快速开始模板

```json
{
  "product_image": "product.jpg",
  "excel_file": "keywords.xlsx",
  "keyword_column": "关键词",
  "similarity_threshold": 0.85,
  "min_matches": 2,
  "amazon_domain": "amazon.com",
  "max_products": 20
}
```

### 高精度模板

```json
{
  "product_image": "product.jpg",
  "excel_file": "keywords.xlsx",
  "keyword_column": "关键词",
  "similarity_threshold": 0.92,
  "min_matches": 5,
  "amazon_domain": "amazon.com",
  "max_products": 30,
  "grid_columns": 10
}
```

### 快速测试模板

```json
{
  "product_image": "product.jpg",
  "excel_file": "test_keywords.xlsx",
  "keyword_column": "关键词",
  "similarity_threshold": 0.75,
  "min_matches": 1,
  "amazon_domain": "amazon.com",
  "max_products": 10,
  "concurrent_workers": 3
}
```

## 配置最佳实践

1. **首次使用**
   - 使用少量关键词（5-10个）测试
   - 从默认阈值 0.85 开始
   - 观察结果并调整

2. **生产环境**
   - 使用配置文件而非命令行参数
   - 启用进度缓存（`--cache`）
   - 定期备份结果

3. **性能优化**
   - 根据机器性能调整 `concurrent_workers`
   - 使用无头模式（`headless=true`）
   - 限制 `max_products` 避免过长等待

4. **安全性**
   - 不要在代码中硬编码 API 密钥
   - 使用环境变量存储敏感信息
   - 不要提交 config.json 到版本控制（添加到 .gitignore）

5. **错误处理**
   - 启用调试模式（`--debug`）诊断问题
   - 使用 `--no-headless` 观察浏览器行为
   - 检查日志文件（如果配置了）

## 故障排查

**配置文件未找到**：
```bash
# 从模板创建
cp .claude/skills/amazon-keyword-filter/assets/config.template.json config.json
```

**环境变量未生效**：
```bash
# 验证环境变量
echo $AMAZON_DOMAIN
env | grep AMAZON
```

**MCP 工具不可用**：
- 检查 `.claude/settings.json` 配置
- 验证 MCP 服务器是否运行
- 确认权限设置正确

更多故障排查，参见 [troubleshooting.md](troubleshooting.md)。

## 配置参考

完整配置选项参考：

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| product_image | string | - | - | 产品图片路径 |
| excel_file | string | - | - | Excel 文件路径 |
| keyword_column | string | "关键词" | - | 关键词列名 |
| similarity_threshold | float | 0.85 | 0.0-1.0 | 相似度阈值 |
| min_matches | integer | 2 | 1+ | 最少匹配数 |
| amazon_domain | string | "amazon.com" | - | Amazon 站点 |
| max_products | integer | 20 | 1-50 | 最多产品数 |
| grid_columns | integer | 5 | 2-10 | 网格列数 |
| concurrent_workers | integer | 5 | 1-10 | 并发线程数 |
| debug | boolean | false | - | 调试模式 |
| headless | boolean | true | - | 无头模式 |
| no_ssl_verify | boolean | false | - | 禁用 SSL |
