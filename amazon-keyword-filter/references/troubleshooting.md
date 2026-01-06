# 故障排查指南

## 环境问题

### ⚠️ 必须使用 uv（重要）

**此 skill 要求使用 uv 进行环境管理**。

**安装 uv**:
```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**验证安装**:
```bash
uv --version
```

### ⚠️ 虚拟环境位置错误（重要）

**错误**: 在 skill 文件夹内创建虚拟环境

**正确做法**:
```bash
# ✓ 正确: 在工作目录使用 uv
cd /c/Projects/my-project  # 你的工作目录
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 或使用自动设置脚本
python .claude/skills/amazon-keyword-filter/scripts/setup_env.py

# ✗ 错误: 在 skill 文件夹创建
cd /c/Projects/auto-work/.claude/skills/amazon-keyword-filter
uv venv  # 不要这样做！
```

**为什么**:
- Skill 文件夹是模板，不是运行环境
- 虚拟环境应该在你实际工作的项目目录
- 每个项目可能有不同的依赖版本
- uv 会自动创建 `.venv` 目录

### ChromeDriver版本不匹配

**错误**:
```
SessionNotCreatedException: session not created: This version of ChromeDriver only supports Chrome version XX
```

**解决方案1: 自动管理**
```bash
uv pip install webdriver-manager
```

修改脚本使用webdriver-manager:
```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
```

**解决方案2: 手动下载**
1. 查看Chrome版本: chrome://version
2. 下载对应ChromeDriver: https://chromedriver.chromium.org/
3. 放到系统PATH或脚本同目录

### 虚拟环境创建失败

**错误**:
```
Failed to create virtual environment
```

**解决**:
```bash
# 清理现有环境
rm -rf .venv

# 重新创建
uv venv

# 验证
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

## 配置问题

### 配置文件不存在

**错误**:
```
FileNotFoundError: config.json not found
```

**解决**:
```bash
# 从示例创建
copy config.example.json config.json  # Windows
cp config.example.json config.json    # Linux/Mac

# 编辑配置
notepad config.json  # Windows
nano config.json     # Linux/Mac
```

### 产品图片不存在

**错误**:
```
FileNotFoundError: my_product.jpg not found
```

**解决**:
1. 确认图片路径正确
2. 图片必须放在项目根目录，或使用绝对路径
3. 检查文件名大小写（Linux区分大小写）

### Excel文件读取失败

**错误**:
```
ValueError: Excel file has no columns named '关键词'
```

**解决**:
1. 打开Excel确认列名
2. 修改config.json中的`keyword_column`匹配实际列名
3. 确保Excel格式为.xlsx（不是.xls或.csv）

## 搜索问题

### 搜索超时

**错误**:
```
TimeoutException: Message:
```

**可能原因**:
- 网络问题
- 亚马逊响应慢
- 页面结构变化

**解决**:
1. 检查网络连接
2. 增加超时时间（修改脚本中的`WebDriverWait(driver, 10)`）
3. 减少并发请求

### IP被封

**现象**:
- 频繁的验证码页面
- 403 Forbidden错误
- 空白搜索结果

**解决**:
1. 增加延迟时间
   ```python
   time.sleep(5)  # 增加到5秒
   ```

2. 减少批次大小
   ```python
   # 每5个关键词暂停
   if i % 5 == 0:
       time.sleep(10)
   ```

3. 使用代理IP（需自行配置）
   ```python
   options.add_argument('--proxy-server=http://proxy:port')
   ```

4. 分时段运行
   - 避开高峰时段
   - 分多天处理大批量关键词

### 图片URL获取失败

**错误**:
```
No images found for keyword: xxx
```

**可能原因**:
- 关键词无搜索结果
- 页面结构变化
- 定位器失效

**解决**:
1. 手动搜索该关键词确认是否有结果
2. 检查亚马逊页面结构是否变化
3. 更新脚本中的CSS选择器

## 图片处理问题

### 图片下载失败

**错误**:
```
Failed to download image: xxx
```

**解决**:
1. 检查网络连接
2. 增加超时时间
3. 跳过失败的图片继续处理

### 相似度计算异常

**错误**:
```
cannot identify image file
```

**可能原因**:
- 图片格式不支持
- 图片损坏
- URL无效

**解决**:
1. 使用try-except包裹处理
2. 记录失败的URL
3. 跳过异常图片

### 内存不足

**错误**:
```
MemoryError
```

**解决**:
1. 减少批次大小
2. 及时关闭图片对象
   ```python
   img.close()
   ```
3. 增加系统内存或使用虚拟内存

## 性能问题

### 处理速度太慢

**优化建议**:

1. **减少每个关键词的商品数**
   ```json
   "max_products": 5  // 从10降到5
   ```

2. **降低图片质量**（修改脚本）
   ```python
   img = img.resize((100, 100))  # 缩小图片
   ```

3. **使用更快的哈希算法**
   ```python
   # 使用average_hash替代phash
   imagehash.average_hash(img)
   ```

4. **并发处理**（注意IP限制）
   ```python
   from concurrent.futures import ThreadPoolExecutor

   with ThreadPoolExecutor(max_workers=3) as executor:
       results = executor.map(process_keyword, keywords)
   ```

### 磁盘空间不足

**解决**:
1. 清理临时文件
2. 不保存中间图片
3. 定期清理缓存

## 结果问题

### 合格率太低 (<5%)

**可能原因**:
- 阈值设置太严格
- 产品图片质量问题
- 关键词不匹配

**解决**:
1. 降低相似度阈值
   ```json
   "similarity_threshold": 0.75
   ```

2. 减少最小匹配数
   ```json
   "min_matches": 1
   ```

3. 检查产品图片是否清晰、正面

### 合格率太高 (>50%)

**可能原因**:
- 阈值设置太宽松
- 图片相似度算法问题

**解决**:
1. 提高相似度阈值
   ```json
   "similarity_threshold": 0.90
   ```

2. 增加最小匹配数
   ```json
   "min_matches": 3
   ```

### Excel导出失败

**错误**:
```
PermissionError: [Errno 13] Permission denied
```

**解决**:
1. 关闭已打开的Excel文件
2. 检查文件权限
3. 更换输出路径

## 调试技巧

### 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 禁用无头模式

查看浏览器操作过程:

```python
# 注释掉这行
# options.add_argument('--headless')
```

### 保存中间结果

```python
# 保存搜索结果
with open('search_results.json', 'w') as f:
    json.dump(image_urls, f)

# 保存相似度结果
with open('similarity_results.json', 'w') as f:
    json.dump(comparison, f)
```

### 单步测试

不要一次处理所有关键词，先测试单个:

```python
# 只测试第一个关键词
keywords = keywords[:1]
```

## 常见问题汇总

| 问题 | 快速解决 |
|------|---------|
| uv未安装 | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| ChromeDriver版本 | `uv pip install webdriver-manager` |
| IP被封 | 增加延迟，减少并发 |
| 处理太慢 | 减少max_products到5 |
| 合格率低 | 降低threshold到0.75 |
| 合格率高 | 提高threshold到0.90 |

## 获取帮助

如果以上方法都无法解决问题:

1. 查看完整错误堆栈
2. 检查Python和依赖版本
3. 尝试在不同环境运行
4. 提供详细的错误信息寻求帮助
