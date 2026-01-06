#!/usr/bin/env python3
"""
使用 MCP AI 分析产品图片，生成用于语义过滤的产品描述

依赖:
- Claude Code CLI (for MCP access)
- zai-mcp-server (图片分析)

使用方法:
    python generate_product_description.py product_image.jpg

输出:
    product_description.json - 包含详细的产品描述
"""

import json
import sys
import os
from pathlib import Path


# ==================== MCP 提示词模板 ====================

PRODUCT_ANALYSIS_PROMPT = """Analyze this product image and provide a comprehensive, structured description optimized for semantic keyword matching.

Please include:

1. **Product Category**: What type of product is this? (e.g., headband, earbuds, backpack, shoes)

2. **Visual Features**:
   - Primary colors (be specific, e.g., "vibrant green", not just "green")
   - Materials/textures visible (e.g., plastic, metal, fabric, glitter, sequins)
   - Shape and design elements
   - Size indicators (if visible)

3. **Purpose/Use Case**:
   - What is this product used for?
   - What occasions/events is it suitable for?
   - Target audience (e.g., women, kids, adults, professionals)

4. **Style/Theme**:
   - Is there a specific theme? (e.g., holiday, sports, fashion, tech)
   - Style descriptors (e.g., festive, minimalist, vintage, modern)

5. **Key Distinguishing Features**:
   - What makes this product unique or recognizable?
   - Any branding, logos, or special design elements

6. **Related Search Terms**:
   - What keywords would someone use to search for this product?
   - Include both generic terms (e.g., "headband") and specific terms (e.g., "St. Patrick's Day headband")

Please provide a detailed, flowing description that includes all these elements naturally. The description will be used for semantic similarity matching with Amazon search keywords, so be thorough and use varied vocabulary that covers different ways people might search for this product.

Focus on objective, observable features rather than subjective opinions."""


# ==================== 核心函数 ====================


def analyze_product_image_with_mcp(image_path: str) -> str:
    """
    使用 MCP AI 分析产品图片

    注意: 这个函数需要在 Claude Code 环境中运行，因为需要访问 MCP 工具

    Args:
        image_path: 产品图片路径

    Returns:
        AI 生成的产品描述文本
    """
    print(f"📸 正在分析产品图片: {image_path}")
    print(f"🤖 调用 MCP AI 分析...")

    # 这里需要用户通过 Claude Code 的 MCP 工具来实现
    # 在实际使用中，这个函数会被 Claude Code 执行，可以访问 MCP

    instruction = f"""
请使用 mcp__zai-mcp-server__analyze_image 工具分析这张产品图片: {image_path}

使用以下提示词:

{PRODUCT_ANALYSIS_PROMPT}

请直接输出 AI 分析结果，不要添加额外的说明。
"""

    print("\n" + "="*70)
    print("⚠️  需要 Claude Code 执行以下 MCP 调用:")
    print("="*70)
    print(instruction)
    print("="*70)

    return None  # 实际使用时会被 MCP 返回的结果替代


def generate_product_description_manual(image_path: str) -> dict:
    """
    手动模式：引导用户输入产品信息

    Args:
        image_path: 产品图片路径（用于参考）

    Returns:
        产品信息字典
    """
    print(f"\n📝 手动输入模式")
    print(f"参考图片: {image_path}")
    print(f"\n请输入产品信息（回车跳过使用默认值）:\n")

    # 基本信息
    name = input("产品名称 [未命名产品]: ").strip() or "未命名产品"
    category = input("产品类别 (e.g., headband, earbuds): ").strip()

    # 视觉特征
    colors = input("主要颜色 (逗号分隔): ").strip()
    materials = input("材质 (逗号分隔): ").strip()

    # 用途
    occasion = input("使用场合 (e.g., party, daily, sports): ").strip()
    target_audience = input("目标人群 (e.g., women, kids, adults): ").strip()

    # 风格
    style = input("风格主题 (e.g., festive, casual, formal): ").strip()

    # 特征
    features = input("关键特征 (逗号分隔): ").strip()

    # 构建描述
    description_parts = [f"This is a {name}"]

    if category:
        description_parts.append(f"in the {category} category")

    if colors:
        description_parts.append(f"featuring {colors} colors")

    if materials:
        description_parts.append(f"made with {materials}")

    if style:
        description_parts.append(f"The style is {style}")

    if occasion:
        description_parts.append(f"suitable for {occasion}")

    if target_audience:
        description_parts.append(f"designed for {target_audience}")

    if features:
        description_parts.append(f"Key features include: {features}")

    description = ". ".join(description_parts) + "."

    return {
        "name": name,
        "category": category,
        "colors": [c.strip() for c in colors.split(",")] if colors else [],
        "materials": [m.strip() for m in materials.split(",")] if materials else [],
        "occasion": occasion,
        "target_audience": target_audience,
        "style": style,
        "features": [f.strip() for f in features.split(",")] if features else [],
        "description": description,
        "image_path": image_path,
        "generation_method": "manual"
    }


def save_product_description(product_info: dict, output_file: str = "product_description.json"):
    """保存产品描述到 JSON 文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(product_info, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 产品描述已保存: {output_file}")
    print(f"\n预览:")
    print(json.dumps(product_info, ensure_ascii=False, indent=2))


# ==================== 主函数 ====================


def main():
    """主流程"""

    if len(sys.argv) < 2:
        print("使用方法: python generate_product_description.py <product_image.jpg> [--manual]")
        print("\n选项:")
        print("  --manual    使用手动输入模式（不调用 MCP AI）")
        sys.exit(1)

    image_path = sys.argv[1]
    manual_mode = "--manual" in sys.argv

    # 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误: 找不到图片文件 {image_path}")
        sys.exit(1)

    print("\n" + "="*70)
    print("🔍 产品描述生成器")
    print("="*70)

    if manual_mode:
        # 手动输入模式
        product_info = generate_product_description_manual(image_path)
    else:
        # MCP AI 分析模式
        print(f"\n⚠️  此脚本需要在 Claude Code 环境中运行以访问 MCP 工具")
        print(f"\n建议使用方式:")
        print(f"  1. 在 Claude Code 中运行此脚本")
        print(f"  2. 或使用 --manual 参数进入手动模式\n")

        # 提示用户
        choice = input("是否使用手动模式? (y/n): ").strip().lower()
        if choice == 'y':
            product_info = generate_product_description_manual(image_path)
        else:
            print("\n请在 Claude Code 环境中运行此脚本以使用 AI 分析功能")
            sys.exit(0)

    # 保存结果
    save_product_description(product_info)

    print("\n💡 下一步:")
    print("  使用生成的 product_description.json 在语义过滤脚本中:")
    print(f"  python demo_zhipu_filter.py")


if __name__ == "__main__":
    main()
