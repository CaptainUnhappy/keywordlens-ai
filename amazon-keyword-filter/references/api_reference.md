# API参考文档

## 脚本命令行接口

### setup_env.py

初始化运行环境。

**用法**:
```bash
python scripts/setup_env.py
```

**功能**:
- 检查uv是否安装
- 检查虚拟环境是否存在
- 创建config.json（如不存在）

**返回码**:
- `0`: 成功
- `1`: 失败

---

### search_amazon.py

在亚马逊搜索关键词并获取商品图片URL。

**用法**:
```bash
python scripts/search_amazon.py <keyword> [amazon_domain] [max_products]
```

**参数**:
- `keyword`: 搜索关键词（必需）
- `amazon_domain`: 亚马逊域名（可选，默认amazon.com）
- `max_products`: 最多获取商品数（可选，默认10）

**示例**:
```bash
# 基本用法
python scripts/search_amazon.py "wireless earbuds"

# 指定站点
python scripts/search_amazon.py "wireless earbuds" amazon.co.jp

# 指定商品数
python scripts/search_amazon.py "wireless earbuds" amazon.com 20
```

**输出** (JSON):
```json
{
  "keyword": "wireless earbuds",
  "image_urls": [
    "https://m.media-amazon.com/images/...",
    "https://m.media-amazon.com/images/..."
  ],
  "count": 10
}
```

**Python API**:
```python
from scripts.search_amazon import search_amazon

image_urls = search_amazon(
    keyword="wireless earbuds",
    amazon_domain="amazon.com",
    max_products=10
)
```

---

### calculate_similarity.py

计算图片相似度。

**用法**:
```bash
# 单个对比
python scripts/calculate_similarity.py <product_image> <compare_image>

# 批量对比（JSON文件）
python scripts/calculate_similarity.py <product_image> <image_urls.json>

# 批量对比（JSON字符串）
python scripts/calculate_similarity.py <product_image> '["url1", "url2"]'
```

**示例**:
```bash
# 对比两张图片
python scripts/calculate_similarity.py product.jpg compare.jpg

# 批量对比
python scripts/calculate_similarity.py product.jpg urls.json
```

**输出** (单个对比):
```json
{
  "similarity": 0.8534,
  "is_match": true
}
```

**输出** (批量对比):
```json
{
  "total": 10,
  "match_count": 5,
  "avg_similarity": 0.7234,
  "results": [
    {
      "index": 0,
      "url": "https://...",
      "similarity": 0.9123,
      "is_match": true
    }
  ]
}
```

**Python API**:
```python
from scripts.calculate_similarity import compare_images, batch_compare

# 单个对比
similarity = compare_images("product.jpg", "compare.jpg")

# 批量对比
result = batch_compare(
    product_image="product.jpg",
    image_urls=["url1", "url2"],
    threshold=0.85,
    hash_algo='phash'
)
```

**哈希算法选项**:
- `phash`: 感知哈希（默认，推荐）
- `ahash`: 平均哈希（更快）
- `dhash`: 差异哈希
- `whash`: 小波哈希（更精确）

---

### process_keywords.py

批量处理关键词。

**用法**:
```bash
python scripts/process_keywords.py [config_path]
```

**参数**:
- `config_path`: 配置文件路径（可选，默认config.json）

**示例**:
```bash
# 使用默认配置
python scripts/process_keywords.py

# 使用指定配置
python scripts/process_keywords.py config_product_a.json
```

**输出**:
- 控制台进度显示
- 生成`process_results.json`
- 更新`keyword_progress.json`

**process_results.json格式**:
```json
[
  {
    "keyword": "wireless earbuds",
    "match_count": 5,
    "avg_similarity": 0.7823,
    "max_similarity": 0.9123,
    "is_qualified": true,
    "similarity_scores": [0.91, 0.88, 0.85, ...]
  }
]
```

**Python API**:
```python
from scripts.process_keywords import process_keywords_from_excel

results = process_keywords_from_excel("config.json")
```

---

### generate_report.py

生成Excel报告。

**用法**:
```bash
python scripts/generate_report.py <results.json> [output.xlsx]
```

**参数**:
- `results.json`: 处理结果JSON文件（必需）
- `output.xlsx`: 输出Excel文件（可选，默认filtered_keywords.xlsx）

**示例**:
```bash
# 基本用法
python scripts/generate_report.py process_results.json

# 指定输出文件
python scripts/generate_report.py process_results.json my_report.xlsx
```

**输出**:
- Excel文件，包含两个工作表:
  - `全部关键词`: 所有处理结果
  - `合格关键词`: 筛选出的高匹配度关键词

**Python API**:
```python
from scripts.generate_report import generate_excel_report

stats = generate_excel_report(
    results_json="process_results.json",
    output_file="filtered_keywords.xlsx"
)
# stats = {"total": 500, "qualified": 87, "qualified_rate": 0.174}
```

---

## Python函数API

### search_amazon模块

#### search_amazon()

```python
def search_amazon(
    keyword: str,
    amazon_domain: str = "amazon.com",
    max_products: int = 10
) -> List[str]
```

在亚马逊搜索关键词并返回商品图片URL列表。

**参数**:
- `keyword`: 搜索关键词
- `amazon_domain`: 亚马逊域名
- `max_products`: 最多获取商品数

**返回**: `List[str]` - 图片URL列表

**异常**:
- `TimeoutException`: 搜索超时
- `WebDriverException`: 浏览器异常

#### init_driver()

```python
def init_driver(headless: bool = True) -> webdriver.Chrome
```

初始化Chrome浏览器驱动。

---

### calculate_similarity模块

#### calculate_image_hash()

```python
def calculate_image_hash(
    image_source: Union[str, bytes],
    hash_algo: str = 'phash'
) -> imagehash.ImageHash
```

计算图片哈希值。

**参数**:
- `image_source`: 图片路径或URL
- `hash_algo`: 哈希算法（phash, ahash, dhash, whash）

**返回**: `imagehash.ImageHash`

#### calculate_similarity()

```python
def calculate_similarity(
    hash1: imagehash.ImageHash,
    hash2: imagehash.ImageHash
) -> float
```

计算两个哈希的相似度。

**返回**: `float` - 相似度 (0-1)

#### compare_images()

```python
def compare_images(
    image1: str,
    image2: str,
    hash_algo: str = 'phash'
) -> float
```

直接对比两张图片的相似度。

**返回**: `float` - 相似度 (0-1)

#### batch_compare()

```python
def batch_compare(
    product_image: str,
    image_urls: List[str],
    threshold: float = 0.85,
    hash_algo: str = 'phash'
) -> dict
```

批量对比产品图片与多个图片。

**返回**:
```python
{
    "total": int,
    "match_count": int,
    "avg_similarity": float,
    "results": List[dict]
}
```

---

### process_keywords模块

#### load_config()

```python
def load_config(config_path: str = "config.json") -> dict
```

加载配置文件。

#### process_single_keyword()

```python
def process_single_keyword(
    keyword: str,
    config: dict,
    progress_cache: dict
) -> dict
```

处理单个关键词。

**返回**:
```python
{
    "keyword": str,
    "match_count": int,
    "avg_similarity": float,
    "max_similarity": float,
    "is_qualified": bool,
    "similarity_scores": List[float]
}
```

#### process_keywords_from_excel()

```python
def process_keywords_from_excel(
    config_path: str = "config.json"
) -> List[dict]
```

从Excel批量处理关键词。

---

### generate_report模块

#### generate_excel_report()

```python
def generate_excel_report(
    results_json: Union[str, List[dict]],
    output_file: str = "filtered_keywords.xlsx"
) -> dict
```

生成Excel报告。

**参数**:
- `results_json`: 结果JSON文件路径或结果列表
- `output_file`: 输出文件路径

**返回**:
```python
{
    "output_file": str,
    "total": int,
    "qualified": int,
    "qualified_rate": float
}
```

---

## 工作流程集成

### 完整流程示例

```python
from scripts.setup_env import setup
from scripts.search_amazon import search_amazon
from scripts.calculate_similarity import batch_compare
from scripts.process_keywords import process_keywords_from_excel
from scripts.generate_report import generate_excel_report

# 1. 初始化环境
setup()

# 2. 处理关键词
results = process_keywords_from_excel("config.json")

# 3. 生成报告
stats = generate_excel_report(results, "filtered_keywords.xlsx")

print(f"合格率: {stats['qualified_rate']:.2%}")
```

### 自定义工作流

```python
# 单个关键词流程
keyword = "wireless earbuds"

# 搜索
image_urls = search_amazon(keyword)

# 对比
comparison = batch_compare("product.jpg", image_urls, threshold=0.85)

# 判断
is_qualified = comparison['match_count'] >= 2

print(f"匹配数: {comparison['match_count']}/10")
print(f"合格: {is_qualified}")
```

---

## 错误处理

所有脚本都应该使用try-except包裹:

```python
try:
    results = process_keywords_from_excel()
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
except ValueError as e:
    print(f"配置错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
    import traceback
    traceback.print_exc()
```

## 性能优化

### 并发处理

```python
from concurrent.futures import ThreadPoolExecutor

def process_batch(keywords):
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(process_single_keyword, keywords)
    return list(results)
```

### 缓存管理

```python
# 读取缓存
progress = load_progress()

# 只处理未缓存的关键词
keywords_to_process = [k for k in keywords if k not in progress]
```

### 内存优化

```python
# 及时关闭图片
img = Image.open(path)
hash_value = imagehash.phash(img)
img.close()  # 释放内存
```
