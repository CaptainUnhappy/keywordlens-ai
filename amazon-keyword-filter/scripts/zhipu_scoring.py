
import os
import requests
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional, Callable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== 配置 ====================
# 获取 API KEY
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
if not ZHIPU_API_KEY:
    # Try one level up if script is run from scripts dir
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

if not ZHIPU_API_KEY:
    print("Warning: ZHIPU_API_KEY not found in environment variables.")
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
EMBEDDING_DIMENSIONS = 2048

def get_embedding(texts: List[str], batch_size: int = 64, progress_callback: Optional[Callable[[int], None]] = None) -> np.ndarray:
    """
    调用智谱AI API获取文本向量（自动分批处理）
    注：这里的 progress_callback 主要用于单纯的一组文本及时的内部反馈，
    但在 score_keywords 里我们会自己控制更复杂的进度逻辑，所以这里默认不传 callback 也可以。
    """
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    all_embeddings = []

    # 分批处理
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for i in range(0, len(texts), batch_size):
        batch_num = i // batch_size + 1
        batch_texts = texts[i : i + batch_size]
        
        # 简单过滤空字符串
        batch_texts = [t for t in batch_texts if t.strip()]
        if not batch_texts:
            continue

        # print(f"📡 ZhipuAI Embedding (Batch {batch_num}/{total_batches}, Size: {len(batch_texts)})...")

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
        
        # Call internal batch callback if needed
        # if progress_callback:
        #     progress_callback(len(all_embeddings))

    return np.array(all_embeddings)

def score_keywords(
    keywords: List[str], 
    product_description: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[Dict]:
    """
    计算关键词与产品描述的相似度分数
    
    progress_callback: func(percent: int, message: str)
    """
    if not keywords or not product_description:
        if progress_callback:
            progress_callback(100, "No input data.")
        return []

    if progress_callback:
        progress_callback(0, "Analyzing product info...")
    
    print(f"📝 Calculating scores for {len(keywords)} keywords against description...")
    
    # 1. 获取产品向量 (10% 进度)
    try:
        product_vec = get_embedding([product_description])[0]
        if progress_callback:
            progress_callback(10, "Product analysis complete. Starting keywords...")
    except Exception as e:
        print(f"❌ Failed to embed product description: {e}")
        if progress_callback:
            progress_callback(100, f"Error: {str(e)}")
        return [{"keyword": kw, "score": 0.0} for kw in keywords]

    # 2. 获取关键词向量 (批次处理)
    # 我们需要手动拆解这一步以便汇报进度
    keyword_vecs = []
    
    BATCH_SIZE = 64
    total_keywords = len(keywords)
    total_batches = (total_keywords + BATCH_SIZE - 1) // BATCH_SIZE
    
    processed_count = 0
    
    # 重新实现分批调用以便插入 progress_callback
    # 原 get_embedding 比较通用，这里为了进度条精细控制，手动循环调用
    
    for i in range(0, total_keywords, BATCH_SIZE):
        batch_slice = keywords[i : i + BATCH_SIZE]
        if not batch_slice:
            continue
            
        current_batch_vecs = get_embedding(batch_slice, batch_size=BATCH_SIZE)
        keyword_vecs.extend(current_batch_vecs)
        
        processed_count += len(batch_slice)
        
        # 计算进度
        # 0-10% 是产品描述
        # 10%-100% 是关键词
        # current = 10 + (processed / total) * 90
        percent = 10 + int((processed_count / total_keywords) * 90)
        # 限制最大 99，等最后一步才 100
        if percent >= 100: percent = 99
        
        print(f"DEBUG: Processed {processed_count}/{total_keywords}, Percent: {percent}%")

        if progress_callback:
            batch_num = i // BATCH_SIZE + 1
            progress_callback(percent, f"Analyzing keywords batch {batch_num}/{total_batches}...")

    keyword_vecs = np.array(keyword_vecs)
    
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
        if i < len(similarities):
             score = float(similarities[i])
        else:
             score = 0.0 # Should not happen if vecs match
             
        results.append({
            "keyword": kw,
            "score": score
        })
    
    # 按分数降序排列
    results.sort(key=lambda x: x["score"], reverse=True)
    
    if progress_callback:
        progress_callback(100, "Analysis Complete.")
        
    return results
