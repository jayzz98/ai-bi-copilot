import powerbi from "powerbi-visuals-api";
import "./../style/visual.less";

export class Visual implements powerbi.extensibility.visual.IVisual {
    private container: HTMLElement;

    constructor(options: powerbi.extensibility.visual.VisualConstructorOptions) {
        this.container = options.element;
        this.container.innerHTML = `
            <div style="font-family:Inter,sans-serif; padding:12px; background:#0a0c14; 
                        height:100%; color:#f0f2f5; display:flex; flex-direction:column; gap:10px;">
                <div style="font-size:16px; font-weight:700; color:#00e8a2;">🧠 AI BI Copilot</div>
                <div style="display:flex; gap:8px;">
                    <input id="ai-input" placeholder="Ask about your data..." 
                        style="flex:1; padding:8px 12px; border-radius:8px; border:1px solid #333;
                               background:#141620; color:#f0f2f5; font-size:13px;" />
                    <button id="ai-ask" 
                        style="padding:8px 16px; background:#00e8a2; color:#0a0c14; 
                               border:none; border-radius:8px; font-weight:700; cursor:pointer;">
                        ASK
                    </button>
                </div>
                <div id="ai-status" style="font-size:12px; color:#888;"></div>
                <div id="ai-insight" 
                    style="background:#141620; border-left:3px solid #00e8a2; padding:10px; 
                           border-radius:6px; font-size:13px; display:none;"></div>
                <div id="ai-table" style="overflow:auto; flex:1;"></div>
            </div>
        `;

        document.getElementById("ai-ask")!.onclick = () => this.handleAsk();
        document.getElementById("ai-input")!.addEventListener("keydown", (e) => {
            if (e.key === "Enter") this.handleAsk();
        });
    }

    private currentData: { columns: string[], rows: object[] } = { columns: [], rows: [] };

    public update(options: powerbi.extensibility.visual.VisualUpdateOptions) {
        const dv = options.dataViews?.[0]?.table;
        if (!dv) return;

        this.currentData.columns = dv.columns.map(c => c.displayName);
        this.currentData.rows = dv.rows.map(row => {
            const obj: any = {};
            dv.columns.forEach((col, i) => { obj[col.displayName] = row[i]; });
            return obj;
        });

        const status = document.getElementById("ai-status")!;
        status.textContent = `✅ ${this.currentData.rows.length.toLocaleString()} rows loaded from Power BI`;
    }

    private async handleAsk() {
        const input = document.getElementById("ai-input") as HTMLInputElement;
        const insight = document.getElementById("ai-insight")!;
        const table = document.getElementById("ai-table")!;
        const status = document.getElementById("ai-status")!;
        const question = input.value.trim();
        if (!question) return;

        status.textContent = "⏳ Thinking...";
        insight.style.display = "none";
        table.innerHTML = "";

        try {
            const resp = await fetch("https://easy-parks-add.loca.lt/ask", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "bypass-tunnel-reminder": "true"
                },
                body: JSON.stringify({
                    question,
                    columns: this.currentData.columns,
                    rows: this.currentData.rows
                })
            });

            const data = await resp.json();
            status.textContent = `✅ Done — ${data.rows.length} rows returned`;

            insight.style.display = "block";
            insight.textContent = "💡 " + data.insight;

            if (data.rows.length > 0) {
                const cols = data.columns;
                let html = `<table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <thead><tr>${cols.map((c: string) => 
                        `<th style="padding:6px 8px; background:#1a1d2e; 
                                    color:#00e8a2; text-align:left; 
                                    border-bottom:1px solid #333;">${c}</th>`
                    ).join("")}</tr></thead><tbody>`;
                
                data.rows.forEach((row: any) => {
                    html += `<tr>${cols.map((c: string) => 
                        `<td style="padding:6px 8px; border-bottom:1px solid #1a1d2e; 
                                    color:#f0f2f5;">${row[c] ?? ""}</td>`
                    ).join("")}</tr>`;
                });
                
                html += "</tbody></table>";
                table.innerHTML = html;
            }

        } catch (err) {
            status.textContent = "❌ Could not reach AI backend. Is FastAPI running?";
        }
    }
}