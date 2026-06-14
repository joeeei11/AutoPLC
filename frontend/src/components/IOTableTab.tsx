import { useState } from "react";
import type { ChatMessage, IOSignal, LLM, SignalType } from "../api";
import { emptySignal, exportIOTableExcel, generateIOTable } from "../api";

const SIGNAL_TYPES: SignalType[] = ["DI", "DO", "AI", "AO"];
const ANALOG_TYPES: SignalType[] = ["AI", "AO"];

interface Props {
  signals: IOSignal[];
  llm: LLM;
  chatMessages: ChatMessage[];
  onChange: (signals: IOSignal[]) => void;
}

export function IOTableTab({ signals, llm, chatMessages, onChange }: Props) {
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateRow(index: number, field: keyof IOSignal, value: string | number | null) {
    const updated = signals.map((s, i) => {
      if (i !== index) return s;
      const next = { ...s, [field]: value } as IOSignal;
      // Clear analog fields when switching to digital
      if (field === "signal_type" && !ANALOG_TYPES.includes(value as SignalType)) {
        next.range_low = null;
        next.range_high = null;
        next.engineering_unit = "";
      }
      return next;
    });
    onChange(updated);
  }

  function addRow() {
    onChange([...signals, emptySignal()]);
  }

  function removeRow(index: number) {
    onChange(signals.filter((_, i) => i !== index));
  }

  async function handleGenerate() {
    if (chatMessages.length === 0) {
      setError("请先在对话 Tab 完成需求梳理");
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await generateIOTable(chatMessages, llm);
      onChange(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  async function handleExport() {
    if (signals.length === 0) {
      setError("I/O 表为空，无法导出");
      return;
    }
    setExporting(true);
    setError(null);
    try {
      await exportIOTableExcel(signals);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    } finally {
      setExporting(false);
    }
  }

  const isAnalog = (sig: IOSignal) => ANALOG_TYPES.includes(sig.signal_type);

  return (
    <div className="io-table-tab">
      {error && (
        <div className="error-box io-table-error" role="alert">
          {error}
        </div>
      )}

      <div className="io-table-scroll">
        {signals.length === 0 ? (
          <div className="io-table-empty">
            暂无信号。点击"生成 I/O 表"让 AI 从对话中提取，或手动添加。
          </div>
        ) : (
          <table className="io-table" aria-label="I/O 分配表">
            <thead>
              <tr>
                <th>Tag</th>
                <th>名称</th>
                <th>类型</th>
                <th>PLC 地址</th>
                <th>模块号</th>
                <th>通道号</th>
                <th>量程低</th>
                <th>量程高</th>
                <th>单位</th>
                <th>注释</th>
                <th aria-label="操作"></th>
              </tr>
            </thead>
            <tbody>
              {signals.map((sig, i) => (
                <tr key={i}>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.tag}
                      onChange={(e) => updateRow(i, "tag", e.target.value)}
                      placeholder="DI001"
                      aria-label={`行 ${i + 1} Tag`}
                    />
                  </td>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.name}
                      onChange={(e) => updateRow(i, "name", e.target.value)}
                      placeholder="信号名称"
                      aria-label={`行 ${i + 1} 名称`}
                    />
                  </td>
                  <td>
                    <select
                      className="io-cell-select"
                      value={sig.signal_type}
                      onChange={(e) => updateRow(i, "signal_type", e.target.value)}
                      aria-label={`行 ${i + 1} 信号类型`}
                    >
                      {SIGNAL_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.plc_address}
                      onChange={(e) => updateRow(i, "plc_address", e.target.value)}
                      placeholder="I0.0"
                      aria-label={`行 ${i + 1} PLC地址`}
                    />
                  </td>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.module_no}
                      onChange={(e) => updateRow(i, "module_no", e.target.value)}
                      aria-label={`行 ${i + 1} 模块号`}
                    />
                  </td>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.channel_no}
                      onChange={(e) => updateRow(i, "channel_no", e.target.value)}
                      aria-label={`行 ${i + 1} 通道号`}
                    />
                  </td>
                  <td>
                    {isAnalog(sig) ? (
                      <input
                        className="io-cell-input io-cell-input--num"
                        type="number"
                        value={sig.range_low ?? ""}
                        onChange={(e) => updateRow(i, "range_low", e.target.value === "" ? null : Number(e.target.value))}
                        aria-label={`行 ${i + 1} 量程低`}
                      />
                    ) : (
                      <span className="io-cell-dash" aria-label="不适用">—</span>
                    )}
                  </td>
                  <td>
                    {isAnalog(sig) ? (
                      <input
                        className="io-cell-input io-cell-input--num"
                        type="number"
                        value={sig.range_high ?? ""}
                        onChange={(e) => updateRow(i, "range_high", e.target.value === "" ? null : Number(e.target.value))}
                        aria-label={`行 ${i + 1} 量程高`}
                      />
                    ) : (
                      <span className="io-cell-dash" aria-label="不适用">—</span>
                    )}
                  </td>
                  <td>
                    {isAnalog(sig) ? (
                      <input
                        className="io-cell-input"
                        value={sig.engineering_unit}
                        onChange={(e) => updateRow(i, "engineering_unit", e.target.value)}
                        placeholder="℃"
                        aria-label={`行 ${i + 1} 工程单位`}
                      />
                    ) : (
                      <span className="io-cell-dash" aria-label="不适用">—</span>
                    )}
                  </td>
                  <td>
                    <input
                      className="io-cell-input"
                      value={sig.comment}
                      onChange={(e) => updateRow(i, "comment", e.target.value)}
                      placeholder="注释"
                      aria-label={`行 ${i + 1} 注释`}
                    />
                  </td>
                  <td>
                    <button
                      className="io-row-delete"
                      onClick={() => removeRow(i)}
                      aria-label={`删除第 ${i + 1} 行`}
                      title="删除"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="io-table-footer">
        <button className="io-add-btn" onClick={addRow} aria-label="新增信号行">
          + 新增信号
        </button>
        <div className="io-table-actions">
          <button
            className="io-gen-btn"
            onClick={handleGenerate}
            disabled={generating}
            aria-label="AI 生成 I/O 表"
          >
            {generating ? "生成中…" : "生成 I/O 表"}
          </button>
          <button
            className="io-export-btn"
            onClick={handleExport}
            disabled={exporting || signals.length === 0}
            aria-label="导出 Excel"
          >
            {exporting ? "导出中…" : "导出 Excel"}
          </button>
        </div>
      </div>
    </div>
  );
}
