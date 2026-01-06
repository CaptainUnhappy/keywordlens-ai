# 测试指南

## 运行测试

### 运行所有测试

```bash
# 在 skill 目录下
python -m unittest discover tests

# 或使用 pytest（如果已安装）
pytest tests/
```

### 运行单个测试文件

```bash
python tests/test_merge_images.py
python tests/test_utils.py
```

### 运行特定测试

```bash
python -m unittest tests.test_utils.TestUtilityFunctions.test_safe_keyword_conversion
```

## 测试覆盖

当前测试覆盖：

- ✅ **test_merge_images.py** - 图片合并功能
  - 网格布局创建
  - 空URL列表处理
  - 网格尺寸计算

- ✅ **test_utils.py** - 工具函数
  - 关键词安全转换
  - 路径创建
  - 时间戳格式
  - 进度跟踪器

## 添加新测试

1. 在 `tests/` 目录创建 `test_*.py` 文件
2. 继承 `unittest.TestCase`
3. 编写测试方法（以 `test_` 开头）
4. 运行测试验证

示例：

```python
import unittest

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        result = my_function()
        self.assertEqual(result, expected_value)
```

## 测试数据

测试数据和fixture放在 `tests/fixtures/` 目录：

```
tests/fixtures/
├── sample_images/     # 测试图片
├── sample_data.json   # 测试数据
└── sample.xlsx        # 测试Excel文件
```

## CI/CD 集成

可以配置 GitHub Actions 自动运行测试：

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python -m unittest discover tests
```

## 注意事项

- 测试不应依赖外部服务（如Amazon、MCP）
- 使用 mock 替代真实的网络请求
- 测试数据应该小巧且可重复
- 清理测试生成的文件
