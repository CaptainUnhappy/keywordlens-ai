const ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions";

export const analyzeImageWithGlm = async (base64Image: string): Promise<{ description: string; category: string; features: string[] }> => {
    const apiKey = process.env.ZHIPU_API_KEY;
    if (!apiKey) {
        throw new Error("ZHIPU_API_KEY not found");
    }

    const cleanBase64 = base64Image.includes('base64,')
        ? base64Image.split('base64,')[1]
        : base64Image;

    const prompt = `
    Analyze this product image for an e-commerce keyword optimization task.
    1. Provide a detailed description of what the product is.
    2. Identify its primary category.
    3. List key visual features, materials, or demographic targets.
    
    Return ONLY valid JSON with keys: "description", "category", "features" (array of strings).
    Do not wrap in markdown code blocks.
  `;

    try {
        const response = await fetch(ZHIPU_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: "glm-4.6v-flash",
                messages: [
                    {
                        role: "user",
                        content: [
                            {
                                type: "image_url",
                                image_url: {
                                    url: base64Image.startsWith('http') ? base64Image : `data:image/jpeg;base64,${cleanBase64}`
                                }
                            },
                            {
                                type: "text",
                                text: prompt
                            }
                        ]
                    }
                ],
                temperature: 0.1,
                top_p: 0.7,
                max_tokens: 1024
            })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Zhipu API Error: ${response.status} - ${errText}`);
        }

        const data = await response.json();
        const content = data.choices?.[0]?.message?.content;

        if (!content) {
            throw new Error("Zhipu/GLM returned no content");
        }

        // Attempt to parse JSON
        // Clean potential markdown blocks like ```json ... ```
        const jsonStr = content.replace(/```json\n?|```/g, '').trim();
        return JSON.parse(jsonStr);

    } catch (error) {
        console.error("GLM Analysis Failed:", error);
        throw error;
    }
};
