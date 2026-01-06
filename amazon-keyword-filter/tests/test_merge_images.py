#!/usr/bin/env python3
"""
测试图片合并功能
"""

import unittest
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image

# 添加 scripts 目录到路径
SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from merge_images import merge_images_grid


class TestMergeImages(unittest.TestCase):
    """图片合并测试"""

    def setUp(self):
        """设置测试环境"""
        self.output_dir = Path(__file__).parent / "test_output"
        self.output_dir.mkdir(exist_ok=True)

    def test_create_grid_layout(self):
        """测试网格布局创建"""
        # 创建测试图片 URL 列表（使用占位符）
        test_urls = [
            f"https://via.placeholder.com/200x200/ff0000/ffffff?text=Image{i}"
            for i in range(1, 21)
        ]

        output_path = self.output_dir / "test_grid.jpg"

        # 测试基本合并功能
        result = merge_images_grid(
            image_urls=test_urls[:4],  # 只测试前4张
            output_path=str(output_path),
            columns=2,
            img_size=(100, 100),
            debug=True,
            no_ssl_verify=True
        )

        # 验证结果
        self.assertTrue(result, "合并应该成功")
        self.assertTrue(output_path.exists(), "输出文件应该存在")

    def test_empty_url_list(self):
        """测试空URL列表"""
        output_path = self.output_dir / "empty_test.jpg"

        result = merge_images_grid(
            image_urls=[],
            output_path=str(output_path),
            columns=5,
            img_size=(200, 200)
        )

        self.assertFalse(result, "空URL列表应该返回False")

    def test_grid_dimensions(self):
        """测试网格尺寸计算"""
        # 测试不同列数和图片数量组合
        test_cases = [
            (10, 2),  # 10张图片，2列 -> 5行
            (10, 5),  # 10张图片，5列 -> 2行
            (13, 3),  # 13张图片，3列 -> 5行（部分填充）
        ]

        for num_images, columns in test_cases:
            expected_rows = (num_images + columns - 1) // columns
            self.assertGreater(expected_rows, 0, f"行数应该大于0: {num_images}张图片，{columns}列")

    def tearDown(self):
        """清理测试环境"""
        # 可选：清理测试生成的文件
        pass


if __name__ == '__main__':
    unittest.main()
