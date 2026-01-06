#!/usr/bin/env python3
"""
测试工具函数
"""

import unittest
import sys
from pathlib import Path

# 添加 scripts 目录到路径
SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestUtilityFunctions(unittest.TestCase):
    """工具函数测试"""

    def test_safe_keyword_conversion(self):
        """测试关键词安全转换"""
        test_cases = [
            ("wireless earbuds", "wireless_earbuds"),
            ("test/keyword", "test_keyword"),
            ("  spaces  ", "spaces"),
        ]

        for input_kw, expected in test_cases:
            safe_kw = input_kw.replace(" ", "_").replace("/", "_").strip()
            self.assertEqual(safe_kw, expected, f"关键词转换失败: {input_kw}")

    def test_path_creation(self):
        """测试路径创建"""
        test_dir = Path(__file__).parent / "test_temp"
        test_dir.mkdir(exist_ok=True)

        self.assertTrue(test_dir.exists(), "目录创建失败")

        # 清理
        test_dir.rmdir()

    def test_timestamp_format(self):
        """测试时间戳格式"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 验证格式
        self.assertEqual(len(timestamp), 15, "时间戳长度应该是15")
        self.assertTrue(timestamp[0:4].isdigit(), "年份应该是数字")
        self.assertEqual(timestamp[8], "_", "应该包含下划线分隔符")


class TestProgressTracker(unittest.TestCase):
    """进度跟踪器测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_cache = Path(__file__).parent / "test_cache.json"

    def test_progress_initialization(self):
        """测试进度跟踪器初始化"""
        sys.path.insert(0, str(SCRIPTS_DIR))
        from batch_analyze_with_ai import ProgressTracker

        tracker = ProgressTracker(str(self.test_cache))

        self.assertIsNotNone(tracker, "跟踪器应该初始化")
        self.assertIsInstance(tracker.get_completed_folders(), set, "应该返回集合")

    def test_add_completed(self):
        """测试添加已完成项"""
        from batch_analyze_with_ai import ProgressTracker

        tracker = ProgressTracker(str(self.test_cache))
        tracker.add_completed("test_folder_1")
        tracker.save()

        completed = tracker.get_completed_folders()
        self.assertIn("test_folder_1", completed, "应该包含已完成的文件夹")

    def tearDown(self):
        """清理测试文件"""
        if self.test_cache.exists():
            self.test_cache.unlink()


if __name__ == '__main__':
    unittest.main()
