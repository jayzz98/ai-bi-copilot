var aICopilot139529B979A14605BDD09BCA3CA85025;
/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ 423
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   b: () => (/* binding */ Visual)
/* harmony export */ });

class Visual {
    container;
    constructor(options) {
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
        document.getElementById("ai-ask").onclick = () => this.handleAsk();
        document.getElementById("ai-input").addEventListener("keydown", (e) => {
            if (e.key === "Enter")
                this.handleAsk();
        });
    }
    currentData = { columns: [], rows: [] };
    update(options) {
        const dv = options.dataViews?.[0]?.table;
        if (!dv)
            return;
        this.currentData.columns = dv.columns.map(c => c.displayName);
        this.currentData.rows = dv.rows.map(row => {
            const obj = {};
            dv.columns.forEach((col, i) => { obj[col.displayName] = row[i]; });
            return obj;
        });
        const status = document.getElementById("ai-status");
        status.textContent = `✅ ${this.currentData.rows.length.toLocaleString()} rows loaded from Power BI`;
    }
    async handleAsk() {
        const input = document.getElementById("ai-input");
        const insight = document.getElementById("ai-insight");
        const table = document.getElementById("ai-table");
        const status = document.getElementById("ai-status");
        const question = input.value.trim();
        if (!question)
            return;
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
                    <thead><tr>${cols.map((c) => `<th style="padding:6px 8px; background:#1a1d2e; 
                                    color:#00e8a2; text-align:left; 
                                    border-bottom:1px solid #333;">${c}</th>`).join("")}</tr></thead><tbody>`;
                data.rows.forEach((row) => {
                    html += `<tr>${cols.map((c) => `<td style="padding:6px 8px; border-bottom:1px solid #1a1d2e; 
                                    color:#f0f2f5;">${row[c] ?? ""}</td>`).join("")}</tr>`;
                });
                html += "</tbody></table>";
                table.innerHTML = html;
            }
        }
        catch (err) {
            status.textContent = "❌ Could not reach AI backend. Is FastAPI running?";
        }
    }
}


/***/ }

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
// This entry needs to be wrapped in an IIFE because it declares 'aICopilot139529B979A14605BDD09BCA3CA85025' on top-level, which conflicts with the current library output.
(() => {
__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (visualPlugin)
/* harmony export */ });
/* harmony import */ var _src_visual__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(423);

var powerbiKey = "powerbi";
var powerbi = window[powerbiKey];
var aICopilot139529B979A14605BDD09BCA3CA85025 = {
    name: 'aICopilot139529B979A14605BDD09BCA3CA85025',
    displayName: 'AICopilot',
    class: 'Visual',
    apiVersion: '5.3.0',
    create: (options) => {
        if (_src_visual__WEBPACK_IMPORTED_MODULE_0__/* .Visual */ .b) {
            return new _src_visual__WEBPACK_IMPORTED_MODULE_0__/* .Visual */ .b(options);
        }
        throw 'Visual instance not found';
    },
    createModalDialog: (dialogId, options, initialState) => {
        const dialogRegistry = globalThis.dialogRegistry;
        if (dialogId in dialogRegistry) {
            new dialogRegistry[dialogId](options, initialState);
        }
    },
    custom: true
};
if (typeof powerbi !== "undefined") {
    powerbi.visuals = powerbi.visuals || {};
    powerbi.visuals.plugins = powerbi.visuals.plugins || {};
    powerbi.visuals.plugins["aICopilot139529B979A14605BDD09BCA3CA85025"] = aICopilot139529B979A14605BDD09BCA3CA85025;
}
/* harmony default export */ const visualPlugin = (aICopilot139529B979A14605BDD09BCA3CA85025);

})();

aICopilot139529B979A14605BDD09BCA3CA85025 = __webpack_exports__;
/******/ })()
;