
import os
import requests
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional

# ==================== 配置 ====================
# 这里应该最好从环境变量或配置文件读取，暂时保留原来 demo 的默认值
ZHIPU_API_KEY = "REDACTED_ZHIPU_KEY"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
EMBEDDING_DIMENSIONS = 2048

def get_embedding(texts: List[str]) -> np.ndarray:
    """
    调用智谱AI API获取文本向量（自动分批处理）
    """
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    BATCH_SIZE = 64 # 根据要求调整为最大值64
    all_embeddings = []

    # 分批处理
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_texts = texts[i : i + BATCH_SIZE]
        
        # 简单过滤空字符串
        batch_texts = [t for t in batch_texts if t.strip()]
        if not batch_texts:
            continue

        print(f"📡 ZhipuAI Embedding (Batch {batch_num}/{total_batches}, Size: {len(batch_texts)})...")

        data = {
            "model": "embedding-3",
            "input": batch_texts,
            "dimensions": EMBEDDING_DIMENSIONS,
        }

        try:
            response = requests.post(ZHIPU_API_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                # 遇到错误填充零向量，防止程序崩溃
                all_embeddings.extend([np.zeros(EMBEDDING_DIMENSIONS)] * len(batch_texts))
                continue

            result = response.json()
            
            if "data" not in result:
                 print(f"❌ API Format Error: {result}")
                 all_embeddings.extend([np.zeros(EMBEDDING_DIMENSIONS)] * len(batch_texts))
                 continue

            # 提取向量
            embeddings = [item["embedding"] for item in result["data"]]
            all_embeddings.extend(embeddings)

        except Exception as e:
            print(f"❌ Request Exception: {e}")
            all_embeddings.extend([np.zeros(EMBEDDING_DIMENSIONS)] * len(batch_texts))

    return np.array(all_embeddings)

def score_keywords(keywords: List[str], product_description: str) -> List[Dict]:
    """
    计算关键词与产品描述的相似度分数
    """
    if not keywords or not product_description:
        return []

    print(f"📝 Calculating scores for {len(keywords)} keywords against description...")
    
    # 1. 获取产品向量
    try:
        product_vec = get_embedding([product_description])[0]
    except Exception as e:
        print(f"❌ Failed to embed product description: {e}")
        return [{"keyword": kw, "score": 0.0} for kw in keywords]

    # 2. 获取关键词向量
    keyword_vecs = get_embedding(keywords)
    
    if len(keyword_vecs) == 0:
        return []

    # 3. 计算相似度
    try:
        # Reshape for scikit-learn: (n_samples, n_features)
        product_vec_reshaped = product_vec.reshape(1, -1)
        similarities = cosine_similarity(product_vec_reshaped, keyword_vecs)[0]
    except Exception as e:
        print(f"❌ Cosine similarity calculation failed: {e}")
        return [{"keyword": kw, "score": 0.0} for kw in keywords]

    # 4. 格式化结果
    results = []
    for i, kw in enumerate(keywords):
        score = float(similarities[i])
        results.append({
            "keyword": kw,
            "score": score
        })
    
    # 按分数降序排列
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
