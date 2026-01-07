
const API_BASE = 'http://localhost:8000/api';

export interface AnalysisStatus {
    status: string;
    progress: number;
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

    async uploadExcel(file: File) {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE}/upload_excel`, {
            method: 'POST',
            body: formData
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

    async performAction(action: 'keep' | 'delete' | 'undecided', index: number) {
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

    async configureReview(config: { include_manual: boolean, include_auto: boolean, include_excluded: boolean }) {
        const res = await fetch(`${API_BASE}/configure_review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return res.json();
    },

    async moveAllToManual() {
        // Now just a wrapper or deprecated
        const res = await fetch(`${API_BASE}/move_all_manual`, { method: 'POST' });
        return res.json();
    },

    async getAllKeywords() {
        const res = await fetch(`${API_BASE}/all_keywords`);
        return res.json();
    },

    async shutdown() {
        try {
            await fetch(`${API_BASE}/shutdown`, { method: 'POST' });
        } catch (e) {
            // Ignore error as server shuts down
        }
    },

    async exportResults() {
        const res = await fetch(`${API_BASE}/export`);
        if (!res.ok) {
            const errText = await res.text();
            try {
                const json = JSON.parse(errText);
                throw new Error(json.detail || "Export failed");
            } catch (e) {
                throw new Error(errText || "Export failed");
            }
        }

        // Trigger download
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `result_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }
};
