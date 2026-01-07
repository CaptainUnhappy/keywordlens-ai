import os
import json
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load env
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

class ZhipuVisionClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or ZHIPU_API_KEY
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY is missing")
        
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def analyze_image_sync(self, reference_base64: str, grid_base64: str, prompt_context: str) -> Dict[str, Any]:
        """
        Synchronously analyze similarity between reference image and search result grid.
        Returns detailed JSON structure.
        """
        
        # Construct specific prompt as requested
        final_prompt = f"""
        任务：作为一名严格的亚马逊选品专家，请判断搜索结果（拼图）是否精准匹配参考产品（主图）。
        参考描述: {prompt_context}

        严格判定标准：
        1. **精准品类锚定**：必须与参考图的核心品类完全一致。
           - **特例（发簪）**：如果参考图是 **“发簪 (Hair Stick)”**，则“发夹 (Hair Clip)”、“发梳 (Comb)”、“抓夹 (Claw)” 等均判为 **NO**。
           - **特例（气球）**：如果参考图是 **“气球 (Balloon)”**，则“打气筒 (Pump)”、“丝带 (Ribbon)”、“单独的横幅 (Banner)” 等配件均判为 **NO**。
        2. **拒绝配件/互补品**：搜索结果的主体必须是产品本身，而不是它的配件或收纳工具。
        3. **拒绝误判**：形状相似但功能不同的产品（如“筷子”误判为“发簪”）必须拒绝。

        请执行：
        1. 计数：统计拼图中明确是**同款/同类主产品**的数量 (Similar Count)。
        2. 评分：给出拼图与参考图的整体匹配置信度 (0.0-1.0)。如果拼图中包含大量不相关杂物，分数应低于 0.5。
        3. 决策：只有当 **(同类主产品数量 / 总产品数) > 50%** 且 **置信度 > 0.6** 时，才返回 YES。否则一律返回 NO。

        请严格返回以下 JSON 格式（不要包含 markdown 代码块）：
        {{
            "decision": "YES" 或 "NO",
            "score": 0.0到1.0的浮点数,
            "reason": "简短的中文理由，包含：主要是什么产品、有多少个匹配 (e.g. '仅发现2个同款，其余均为配件')",
            "similar_count": 整数，匹配数量
        }}
        """

        payload = {
            "model": "glm-4.6v-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": reference_base64 if reference_base64.startswith("http") else f"data:image/jpeg;base64,{reference_base64}"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": grid_base64 if grid_base64.startswith("http") else f"data:image/jpeg;base64,{grid_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": final_prompt
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "top_p": 0.7, 
            "max_tokens": 1024
        }

        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            res_json = response.json()
            content = res_json['choices'][0]['message']['content']
            
            # Clean content if needed (sometimes LLM adds ```json)
            clean_content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                result_data = json.loads(clean_content)
                # Ensure keys exist
                if "decision" not in result_data: result_data["decision"] = "NO"
                if "reason" not in result_data: result_data["reason"] = content[:50]
                return result_data
            except json.JSONDecodeError:
                # Fallback if raw text
                is_yes = "YES" in content.upper() or "是" in content
                return {
                    "decision": "YES" if is_yes else "NO",
                    "score": 0.5,
                    "reason": content[:100],
                    "similar_count": 0
                }

        except Exception as e:
            print(f"Zhipu Sync API Error: {e}")
            return {
                "decision": "NO",
                "score": 0.0,
                "reason": f"API Error: {str(e)}",
                "similar_count": 0
            }

if __name__ == "__main__":
    # Test stub
    pass
