
const API_BASE = 'http://localhost:8000/api';

export interface AnalysisStatus {
    status: string;
    manual_count: number;
    auto_count: number;
    excluded_count: number;
    manual_pending: number;
    current_manual_index: number;
    current_keyword: {
        keyword: string;
        score: number;
        status: string;
    } | null;
}

export const api = {
    async analyze(keywords: string[], productDescription: string) {
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords, product_description: productDescription })
        });
        return res.json();
    },

    async getStatus(): Promise<AnalysisStatus> {
        const res = await fetch(`${API_BASE}/status`);
        return res.json();
    },

    async getManualQueue() {
        const res = await fetch(`${API_BASE}/manual_queue`);
        return res.json();
    },

    async performAction(action: 'keep' | 'delete', index: number) {
        const res = await fetch(`${API_BASE}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, index })
        });
        return res.json();
    },

    async navigateTo(index: number) {
        const res = await fetch(`${API_BASE}/navigate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
        });
        return res.json();
    },

    async shutdown() {
        try {
            await fetch(`${API_BASE}/shutdown`, { method: 'POST' });
        } catch (e) {
            // Ignore error as server shuts down
        }
    }
};
