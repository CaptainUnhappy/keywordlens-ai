import { GoogleGenAI, Type, Schema } from "@google/genai";
import { KeywordItem } from "../types";

// Initialize AI client
const getAiClient = () => {
  const apiKey = process.env.API_KEY;
  if (!apiKey) {
    throw new Error("API Key not found. Please set process.env.API_KEY");
  }
  return new GoogleGenAI({ apiKey });
};

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Retry wrapper for API calls to handle rate limits
async function withRetry<T>(operation: () => Promise<T>, retries = 5, initialDelay = 2000): Promise<T> {
  try {
    return await operation();
  } catch (error: any) {
    const errorMsg = error.toString().toLowerCase();
    // 404 errors usually mean wrong model name, so retrying won't help, but we keep the logic for quotas (429)
    const isQuotaError = errorMsg.includes('429') ||
      errorMsg.includes('quota') ||
      errorMsg.includes('resource exhausted') ||
      errorMsg.includes('limit');

    if (retries > 0 && isQuotaError) {
      console.warn(`Quota hit, retrying in ${initialDelay}ms... (${retries} attempts left)`);
      await delay(initialDelay);
      return withRetry(operation, retries - 1, initialDelay * 2);
    }
    throw error;
  }
}

// Zhipu AI Configuration
// Note: In production, use process.env.ZHIPU_API_KEY
const getZhipuKey = () => {
  try {
    return process.env.ZHIPU_API_KEY;
  } catch (e) {
    return undefined;
  }
};
const ZHIPU_API_KEY = getZhipuKey() || "REDACTED_ZHIPU_KEY";
const ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions";

export const analyzeProductImage = async (base64Image: string): Promise<{ description: string; category: string; features: string[] }> => {
  return withRetry(async () => {
    const prompt = `
      Analyze this product image for an e-commerce keyword optimization task.
      1. Provide a detailed description of what the product is.
      2. Identify its primary category.
      3. List key visual features, materials, or demographic targets.
      
      Output strictly in JSON format with the following structure:
      {
        "description": "string",
        "category": "string",
        "features": ["string", "string"]
      }
    `;

    const payload = {
      model: "glm-4v-flash",
      messages: [
        {
          role: "user",
          content: [
            {
              type: "text",
              text: prompt
            },
            {
              type: "image_url",
              image_url: {
                url: (base64Image.startsWith('http') || base64Image.startsWith('data:'))
                  ? base64Image
                  : `data:image/jpeg;base64,${base64Image}`
              }
            }
          ]
        }
      ],
      temperature: 0.1
    };

    const response = await fetch(ZHIPU_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ZHIPU_API_KEY}`
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error("Zhipu API Error Details:", errText);
      throw new Error(`Zhipu API Error: ${response.status} - ${errText}`);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;

    if (!content) throw new Error("No content received from Zhipu AI");

    // Clean up markdown code blocks if present
    const jsonString = content.replace(/```json\n?|\n?```/g, '').trim();

    try {
      return JSON.parse(jsonString);
    } catch (e) {
      console.error("Failed to parse Zhipu response:", content);
      throw new Error("Invalid JSON response from AI");
    }
  });
};

export const batchScoreKeywords = async (
  keywords: string[],
  productContext: string
): Promise<{ keyword: string; score: number; reasoning: string }[]> => {
  return withRetry(async () => {
    const ai = getAiClient();

    const prompt = `
      Context: We are screening search keywords for a product described as: "${productContext}".
      
      Task: Rate the relevance of the following keywords on a scale of 0 to 100.
      - 90-100: Exact match, high intent (e.g., exact product name).
      - 70-89: Highly relevant, broad match (e.g., product category + feature).
      - 40-69: Loosely related, needs human check (e.g., competitor names, vague terms).
      - 0-39: Irrelevant or negative match.

      Keywords to score:
      ${JSON.stringify(keywords)}

      Return a JSON array.
    `;

    // Use gemini-2.0-flash-exp for fast text processing
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              keyword: { type: Type.STRING },
              score: { type: Type.NUMBER },
              reasoning: { type: Type.STRING }
            },
            required: ["keyword", "score", "reasoning"]
          }
        }
      }
    });

    if (!response.text) return [];
    return JSON.parse(response.text);
  });
};

// Simulate the "Machine Verification" step
export const machineVerifyKeyword = async (keyword: string, productContext: string, imageBase64: string): Promise<boolean> => {
  return withRetry(async () => {
    const ai = getAiClient();

    const prompt = `
        Strict Verification Mode.
        Product: ${productContext}
        Keyword: "${keyword}"
        
        Does this keyword accurately describe the product image provided? 
        Imagine a user searching for "${keyword}" - would they be satisfied finding this product?
        Return true if it is a good match, false otherwise.
      `;

    // Use gemini-2.0-flash-exp for deep check
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: {
        parts: [
          { inlineData: { mimeType: 'image/jpeg', data: imageBase64 } },
          { text: prompt }
        ]
      },
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            isMatch: { type: Type.BOOLEAN }
          }
        }
      }
    });

    if (!response.text) return false;
    const res = JSON.parse(response.text);
    return res.isMatch;
  });
};