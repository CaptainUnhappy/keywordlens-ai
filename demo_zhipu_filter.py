#!/usr/bin/env python3
"""
智谱AI Embedding-3 关键词过滤演示
对比图片产品与关键词列表的语义相似度
"""

import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
from typing import List, Dict
import pandas as pd
import os

# ==================== 配置 ====================

# 智谱AI API配置
ZHIPU_API_KEY = "REDACTED_ZHIPU_KEY"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
EMBEDDING_DIMENSIONS = 2048  # 使用2048维向量（最高精度）

# ==================== MCP AI 生成的产品描述 ====================
# 此描述由 MCP zai-mcp-server 的 analyze_image 工具自动生成
# 生成方法: 在 Claude Code 中调用
#   mcp__zai-mcp-server__analyze_image(
#       image_source="微信图片_20260104145736.png",
#       prompt="分析产品特征用于语义匹配..."
#   )

MCP_GENERATED_DESCRIPTION = """This image showcases a festive headband, specifically designed as a St. Patrick's Day accessory. The product is a vibrant green headband adorned with multiple shiny shamrock (clover) decorations and a fringe of green tinsel-like material, making it instantly recognizable as a holiday-themed hair accessory.

Product Category: This is a headband or hair accessory, designed to be worn on the head.

Visual Features: Bright vivid green color throughout. Materials include flexible plastic/foam band, shiny glittery plastic shamrocks with reflective quality, and thin tinsel-like green fringe. Standard U-shaped headband design with decorative front panel densely packed with shamrock shapes and green fringe.

Purpose/Use Case: Festive hair accessory for St. Patrick's Day celebrations, parties, parades, Irish festivals, and themed events. Target audience includes kids, teens, and adults.

Style/Theme: St. Patrick's Day or Irish themed. Style is festive, party, costume, playful, and decorative.

Key Features: Multiple shiny shamrock decorations, green fringe, shamrock symbolism linking to Irish culture, vibrant consistent green color.

Related Search Terms: headband, hair accessory, St. Patrick's Day headband, shamrock headband, clover headband, green headband, St. Paddy's Day headband, Irish headband, party headband, costume accessory, festive headband, holiday headband, St. Patrick's Day hair accessory, St. Patrick's Day costume."""

# 产品信息（用于语义匹配）
PRODUCT_INFO = {
    "description": MCP_GENERATED_DESCRIPTION,
    "generation_method": "MCP AI (zai-mcp-server)",
    "image_source": "微信图片_20260104145736.png"
}


# Excel 文件配置
EXCEL_FILE = "圣帕发箍.xlsx"
KEYWORD_COLUMN = "关键词"

# 相似度阈值
SIMILARITY_THRESHOLD = 0.6


# ==================== 辅助函数 ====================


def load_keywords_from_excel(file_path: str, column_name: str) -> List[str]:
    """
    从 Excel 文件中读取关键词列

    Args:
        file_path: Excel 文件路径
        column_name: 列名

    Returns:
        关键词列表
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到 Excel 文件: {file_path}")

    print(f"📂 正在读取文件: {file_path}")
    df = pd.read_excel(file_path)

    if column_name not in df.columns:
        raise ValueError(
            f"Excel 文件中没有找到列 '{column_name}'，可用列: {list(df.columns)}"
        )

    # 提取关键词，去除空值和空白
    keywords = df[column_name].dropna().str.strip().tolist()
    keywords = [kw for kw in keywords if kw]

    print(f"✓ 成功读取 {len(keywords)} 个关键词")
    return keywords


# ==================== 核心函数 ====================


def get_embedding(texts: List[str]) -> np.ndarray:
    """
    调用智谱AI API获取文本向量（自动分批处理）

    Args:
        texts: 文本列表（自动分批，每批最多64条）

    Returns:
        numpy数组，shape=(len(texts), dimensions)
    """
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    BATCH_SIZE = 64
    all_embeddings = []

    # 分批处理
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_texts = texts[i : i + BATCH_SIZE]

        print(
            f"📡 调用智谱AI API (批次 {batch_num}/{total_batches}, 数量: {len(batch_texts)})..."
        )

        data = {
            "model": "embedding-3",
            "input": batch_texts,
            "dimensions": EMBEDDING_DIMENSIONS,
        }

        response = requests.post(ZHIPU_API_URL, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"API调用失败: {response.status_code}\n{response.text}")

        result = response.json()

        # 提取向量
        embeddings = [item["embedding"] for item in result["data"]]
        all_embeddings.extend(embeddings)

        # 记录使用情况
        usage = result.get("usage", {})
        print(f"  ✓ 消耗tokens: {usage.get('total_tokens', 'N/A')}")

    return np.array(all_embeddings)


def generate_product_description(product_info: Dict) -> str:
    """
    从产品信息生成描述文本（基于 MCP AI 分析）

    Args:
        product_info: 产品信息字典

    Returns:
        产品描述字符串
    """
    # 使用 MCP AI 分析的详细描述
    base_description = product_info.get("description", "")

    # 添加 MCP 识别的关键搜索词
    keywords = [
        "St. Patrick's Day headband",
        "Shamrock headband",
        "Green headband",
        "Clover headband",
        "Irish headband",
        "Party headband",
        "Costume headband",
        "Festive hair accessory",
        "St. Patrick's Day accessory",
        "Green tinsel headband",
        "Holiday headband",
        "St. Paddy's Day headband",
        "Irish costume accessory",
        "Glitter shamrock headband",
        "Sequined headband",
        "Festival hair accessory",
    ]

    # 组合描述
    description = f"{base_description} {' '.join(keywords)}"
    return description


def filter_keywords(
    keywords: List[str], product_description: str, threshold: float = 0.5
) -> Dict:
    """
    使用智谱AI Embedding过滤关键词

    Args:
        keywords: 关键词列表
        product_description: 产品描述
        threshold: 相似度阈值

    Returns:
        过滤结果字典
    """
    # 获取产品描述向量
    print(f"\n📝 产品描述: {product_description}\n")
    product_vec = get_embedding([product_description])[0]

    # 获取关键词向量
    print(f"\n🔄 编码 {len(keywords)} 个关键词...")
    keyword_vecs = get_embedding(keywords)

    # 计算余弦相似度
    print(f"\n📊 计算语义相似度...\n")
    similarities = cosine_similarity([product_vec], keyword_vecs)[0]

    # 排序
    keyword_scores = list(zip(keywords, similarities))
    keyword_scores.sort(key=lambda x: x[1], reverse=True)

    # 过滤
    filtered = [(kw, score) for kw, score in keyword_scores if score >= threshold]

    # 统计
    stats = {
        "total": len(keywords),
        "filtered": len(filtered),
        "removed": len(keywords) - len(filtered),
        "filter_rate": 1 - len(filtered) / len(keywords),
        "pass_rate": len(filtered) / len(keywords),
        "avg_score": float(np.mean(similarities)),
        "max_score": float(similarities.max()),
        "min_score": float(similarities.min()),
        "threshold": threshold,
    }

    return {
        "filtered_keywords": [kw for kw, _ in filtered],
        "all_scores": {kw: float(score) for kw, score in keyword_scores},
        "top_keywords": keyword_scores,
        "stats": stats,
    }


def print_results(result: Dict):
    """打印格式化结果"""
    stats = result["stats"]
    top_keywords = result["top_keywords"]

    print("=" * 70)
    print("智谱AI Embedding-3 语义过滤结果")
    print("=" * 70)

    # 统计信息
    print(f"\n📊 统计信息:")
    print(f"  总关键词数:   {stats['total']}")
    print(f"  通过筛选:     {stats['filtered']} ({stats['pass_rate']:.1%})")
    print(f"  被过滤:       {stats['removed']} ({stats['filter_rate']:.1%})")
    print(f"  相似度阈值:   {stats['threshold']}")
    print(f"  分数范围:     {stats['min_score']:.3f} - {stats['max_score']:.3f}")
    print(f"  平均分数:     {stats['avg_score']:.3f}")

    # 分数分布
    print(f"\n📈 分数分布:")
    score_ranges = {
        "优秀 (0.8-1.0)": [kw for kw, s in top_keywords if s >= 0.8],
        "良好 (0.6-0.8)": [kw for kw, s in top_keywords if 0.6 <= s < 0.8],
        "中等 (0.4-0.6)": [kw for kw, s in top_keywords if 0.4 <= s < 0.6],
        "较低 (0-0.4)": [kw for kw, s in top_keywords if s < 0.4],
    }

    for range_name, kws in score_ranges.items():
        count = len(kws)
        pct = count / stats["total"] * 100
        bar = "█" * int(pct / 2)
        print(f"  {range_name}: {count:2d} ({pct:5.1f}%) {bar}")

    # 详细列表
    print(f"\n📋 关键词详细得分:")
    print(f"{'排名':<5} {'状态':<5} {'得分':<8} {'关键词'}")
    print("-" * 70)

    for i, (kw, score) in enumerate(top_keywords, 1):
        status = "✓ 通过" if score >= stats["threshold"] else "✗ 过滤"
        color_code = "\033[92m" if score >= stats["threshold"] else "\033[91m"
        reset_code = "\033[0m"

        print(f"{i:<5} {color_code}{status:<5}{reset_code} {score:<8.4f} {kw}")

    print("=" * 70)


def save_results(result: Dict, filename: str = "zhipu_filter_result.json"):
    """保存结果到JSON文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON结果已保存: {filename}")


def save_to_excel(
    result: Dict,
    excel_file: str,
    keyword_column: str,
    score_column: str = "相似度得分",
    status_column: str = "状态",
    output_file: str = None,
):
    """
    将过滤结果写回Excel文件，在关键词列右侧插入得分列

    Args:
        result: 过滤结果字典
        excel_file: 原Excel文件路径
        keyword_column: 关键词列名
        score_column: 得分列名（默认"相似度得分"）
        status_column: 状态列名（默认"状态"）
        output_file: 输出文件名（默认在原文件名后加"_result"）
    """
    if output_file is None:
        name, ext = os.path.splitext(excel_file)
        output_file = f"{name}_result{ext}"

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    # 确保关键词列存在
    if keyword_column not in df.columns:
        print(f"⚠️  警告: Excel中没有找到'{keyword_column}'列，跳过Excel写入")
        return

    # 创建得分和状态映射
    all_scores = result["all_scores"]
    threshold = result["stats"]["threshold"]

    # 添加得分列
    df[score_column] = df[keyword_column].map(lambda x: all_scores.get(x, np.nan))

    # 添加状态列
    def get_status(score):
        if pd.isna(score):
            return "无数据"
        return "✓ 通过" if score >= threshold else "✗ 过滤"

    df[status_column] = df[score_column].apply(get_status)

    # 找到关键词列的位置
    col_idx = df.columns.get_loc(keyword_column)

    # 重新排列列：将得分和状态列放在关键词列后面
    cols = list(df.columns)
    cols.remove(score_column)
    cols.remove(status_column)
    # 在关键词列后插入得分列和状态列
    insert_idx = col_idx + 1
    cols.insert(insert_idx, score_column)
    cols.insert(insert_idx + 1, status_column)
    df = df[cols]

    # 保存到新文件
    df.to_excel(output_file, index=False)
    print(f"💾 Excel结果已保存: {output_file}")
    print(
        f"   已插入列: '{score_column}' 和 '{status_column}' 到 '{keyword_column}' 右侧"
    )


# ==================== 主函数 ====================


def main():
    """主流程"""
    print("\n" + "=" * 70)
    print("🍀 St. Patrick's Day 头饰 - 关键词语义过滤演示")
    print("=" * 70)

    # 显示产品信息
    print(f"\n📦 产品信息:")
    # print(f"  名称: {PRODUCT_INFO['name']}")
    # print(f"  类别: {PRODUCT_INFO['category']}")
    # print(f"  颜色: {PRODUCT_INFO['color']}")
    # print(f"  风格: {PRODUCT_INFO['style']}")
    # print(f"  特征: {', '.join(PRODUCT_INFO['features'][:3])}...")

    # 从 Excel 文件加载关键词
    try:
        test_keywords = load_keywords_from_excel(EXCEL_FILE, KEYWORD_COLUMN)
    except Exception as e:
        print(f"\n❌ 加载关键词失败: {e}")
        return

    print(f"\n🔍 待测试关键词数量: {len(test_keywords)}")
    print(f"📏 相似度阈值: {SIMILARITY_THRESHOLD}")
    print(f"🎯 向量维度: {EMBEDDING_DIMENSIONS}")

    # 生成产品描述
    product_description = generate_product_description(PRODUCT_INFO)

    # 过滤关键词
    try:
        result = filter_keywords(
            keywords=test_keywords,
            product_description=product_description,
            threshold=SIMILARITY_THRESHOLD,
        )

        # 打印结果
        print_results(result)

        # 保存结果到JSON
        save_results(result)

        # 保存结果到Excel
        save_to_excel(
            result=result, excel_file=EXCEL_FILE, keyword_column=KEYWORD_COLUMN
        )

        # 成本估算
        total_tokens = result["stats"]["total"] * 5 + 50  # 估算
        cost = (total_tokens / 1_000_000) * 0.5
        print(f"\n💰 预估成本: ¥{cost:.6f} (~{total_tokens} tokens)")

        print("\n✅ 过滤完成！")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
