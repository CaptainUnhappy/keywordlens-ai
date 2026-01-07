import { GoogleGenAI, Type, Schema } from "@google/genai";
import { KeywordItem } from "../types";

// Initialize AI client
const getAiClient = () => {
  const apiKey = process.env.GEMINI_API_KEY; // Fallback to safe
  if (!apiKey) {
    throw new Error("API Key not found. Please set process.env.GEMINI_API_KEY");
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

export const analyzeProductImage = async (base64Image: string): Promise<{ description: string; category: string; features: string[] }> => {
  // Try Gemini first with a timeout
  try {
    const ai = getAiClient();

    const cleanBase64 = base64Image.includes('base64,')
      ? base64Image.split('base64,')[1]
      : base64Image;

    const prompt = `
      Analyze this product image for an e-commerce keyword optimization task.
      1. Provide a detailed description of what the product is.
      2. Identify its primary category.
      3. List key visual features, materials, or demographic targets.
    `;

    const geminiPromise = ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: [
        {
          role: 'user',
          parts: [
            { inlineData: { mimeType: 'image/jpeg', data: cleanBase64 } },
            { text: prompt }
          ]
        }
      ],
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            description: { type: Type.STRING },
            category: { type: Type.STRING },
            features: {
              type: Type.ARRAY,
              items: { type: Type.STRING }
            }
          },
          required: ["description", "category", "features"]
        }
      }
    });

    // 15 seconds timeout for Gemini
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Gemini Request Timed Out")), 15000)
    );

    const response = await Promise.race([geminiPromise, timeoutPromise]) as any;

    if (!response.text) throw new Error("No content received from Gemini AI");

    // Parse the JSON response directly
    return JSON.parse(response.text);

  } catch (error) {
    console.warn("Gemini Analysis Failed or Timed Out, switching to Zhipu (GLM)...", error);
    // Dynamic import to avoid circular dep issues if any, or just clean separation
    const { analyzeImageWithGlm } = await import('./glm');
    return await analyzeImageWithGlm(base64Image);
  }
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