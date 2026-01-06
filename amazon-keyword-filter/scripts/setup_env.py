#!/usr/bin/env python3
"""
环境初始化脚本
检查并设置运行环境
"""

import sys
import os
import subprocess
import json


def check_uv():
    """检查uv是否安装"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✓ uv {version}")
            return True
    except FileNotFoundError:
        pass

    print("✗ uv 未安装")
    print("  安装: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
    return False


def check_venv():
    """检查虚拟环境"""
    if os.path.exists('.venv'):
        print("✓ 虚拟环境存在")
        return True

    print("✗ 虚拟环境不存在")
    return False


def create_venv():
    """创建虚拟环境"""
    print("创建虚拟环境...")
    result = subprocess.run(['uv', 'venv'], capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ 虚拟环境已创建")
        return True
    else:
        print(f"✗ 创建失败: {result.stderr}")
        return False


def install_dependencies():
    """安装依赖"""
    print("安装依赖...")

    # 需要的依赖包
    packages = [
        'selenium>=4.15.0',
        'requests>=2.31.0',
        'Pillow>=10.0.0',
        'imagehash>=4.3.1',
        'pandas>=2.0.0',
        'openpyxl>=3.1.0'
    ]

    result = subprocess.run(
        ['uv', 'pip', 'install'] + packages,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ 依赖已安装")
        print("  已安装: selenium, requests, Pillow, imagehash, pandas, openpyxl")
        return True
    else:
        print(f"✗ 安装失败: {result.stderr}")
        return False


def check_config():
    """检查配置文件"""
    if os.path.exists('config.json'):
        print("✓ config.json 存在")
        return True

    if os.path.exists('config.example.json'):
        print("✗ config.json 不存在，从示例创建...")
        with open('config.example.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print("✓ config.json 已创建，请编辑配置")
        return False

    print("✗ config.example.json 不存在")
    return False


def setup():
    """完整的环境设置"""
    print("=" * 60)
    print("环境初始化")
    print("=" * 60)
    print()

    # 1. 检查uv
    print("[1/4] 检查uv")
    if not check_uv():
        print()
        print("请先安装uv:")
        print("  Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        print("  Linux/Mac: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    print()

    # 2. 检查/创建虚拟环境
    print("[2/4] 检查虚拟环境")
    if not check_venv():
        print()
        if not create_venv():
            return False
    print()

    # 3. 安装依赖
    print("[3/4] 安装依赖")
    if not install_dependencies():
        return False
    print()

    # 4. 检查配置
    print("[4/4] 检查配置文件")
    config_ok = check_config()
    print()

    # 总结
    print("=" * 60)
    if config_ok:
        print("环境就绪!")
        print("=" * 60)
        print()
        print("下一步:")
        print("  1. 准备产品图片和Excel文件")
        print("  2. 运行: python scripts/process_keywords.py")
        return True
    else:
        print("环境设置完成，需要配置")
        print("=" * 60)
        print()
        print("下一步:")
        print("  1. 编辑 config.json，配置产品图片和Excel路径")
        print("  2. 准备产品图片和Excel文件")
        print("  3. 运行: python scripts/process_keywords.py")
        return True


def main():
    """命令行入口"""
    success = setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
