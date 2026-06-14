import { useState } from "react";
import Editor from "@monaco-editor/react";
import type { PLCProgram, ValidationErrorItem } from "../api";
import { exportPLC } from "../api";
import { SimulationPanel } from "./SimulationPanel";

interface Props {
  stCode: string;
  plcProgram: PLCProgram | null;
  validationErrors: ValidationErrorItem[];
  rerendering: boolean;
  theme: "dark" | "light";
  onChange: (code: string) => void;
  onRerender: () => void;
}

export function RightPanel({
  stCode,
  plcProgram,
  validationErrors,
  rerendering,
  theme,
  onChange,
  onRerender,
}: Props) {
  const canExport = plcProgram !== null;
  const [copied, setCopied] = useState(false);

  async function handleExport(brand: "generic" | "siemens" | "rockwell") {
    if (!plcProgram) return;
    try {
      await exportPLC(plcProgram, brand);
    } catch {
      // 静默失败，不打断用户
    }
  }

  async function handleCopy() {
    if (!stCode) return;
    await navigator.clipboard.writeText(stCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <aside className="right-panel">
      <div className="right-panel-header">
        <h2 className="panel-title">ST 代码</h2>
        <div className="right-panel-header-btns">
          <button
            className="copy-btn"
            onClick={handleCopy}
            disabled={!stCode}
            aria-label="复制 ST 代码"
          >
            {copied ? "已复制" : "复制"}
          </button>
          <button
            className="rerender-btn"
            onClick={onRerender}
            disabled={rerendering || !stCode}
          >
            {rerendering ? "渲染中…" : "重新渲染"}
          </button>
        </div>
      </div>

      <div className="monaco-wrapper">
        <Editor
          height="100%"
          defaultLanguage="pascal"
          value={stCode}
          onChange={(v) => onChange(v ?? "")}
          theme={theme === "dark" ? "vs-dark" : "vs"}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            wordWrap: "on",
            scrollBeyondLastLine: false,
          }}
        />
      </div>

      <div className="export-bar">
        <span className="export-label">导出</span>
        <button
          className="export-btn"
          disabled={!canExport}
          onClick={() => handleExport("generic")}
        >
          下载 .st
        </button>
        <button
          className="export-btn"
          disabled={!canExport}
          onClick={() => handleExport("siemens")}
        >
          下载 .scl
        </button>
        <button
          className="export-btn"
          disabled={!canExport}
          onClick={() => handleExport("rockwell")}
        >
          下载 .L5X
        </button>
      </div>

      {validationErrors.length > 0 && (
        <ul className="validation-errors" role="list" aria-label="验证错误">
          {validationErrors.map((e, i) => (
            <li
              key={i}
              className={`validation-error-item${e.rule === "naming_convention" ? " validation-error-item--warn" : ""}`}
            >
              <strong>[{e.rule}]</strong> {e.message}
            </li>
          ))}
        </ul>
      )}

      <SimulationPanel stCode={stCode} />
    </aside>
  );
}
