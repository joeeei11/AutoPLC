import { useEffect, useRef, useState } from "react";
import {
  getSimulationStatus,
  startSimulation,
  type SimulationStatus,
} from "../api";

interface Props {
  stCode: string;
}

const STATUS_LABEL: Record<SimulationStatus, string> = {
  compiling: "编译中",
  running: "运行中",
  error: "错误",
};

export function SimulationPanel({ stCode }: Props) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [variables, setVariables] = useState<Record<string, unknown>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const disabled = !stCode.trim();

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      try {
        const res = await getSimulationStatus(taskId);
        if (cancelled) return;
        setStatus(res.status);
        setVariables(res.variables);
        setErrorMessage(res.status === "error" ? formatError(res.error_message ?? "") : null);
      } catch {
        if (cancelled) return;
        setStatus("error");
        setVariables({});
        setErrorMessage("仿真器无法连接，请确认 Docker 已启动");
      }
    };

    poll();
    const id = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [taskId]);

  async function handleStart() {
    if (disabled || starting) return;
    setStarting(true);
    setStatus("compiling");
    setVariables({});
    setErrorMessage(null);
    setTaskId(null);
    try {
      const { task_id } = await startSimulation(stCode);
      setTaskId(task_id);
    } catch {
      setStatus("error");
      setErrorMessage("仿真器无法连接，请确认 Docker 已启动");
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="sim-panel">
      <div className="sim-bar">
        <span className="sim-label">仿真</span>
        <button
          className="sim-btn"
          disabled={disabled || starting}
          onClick={handleStart}
          aria-label="开始仿真"
        >
          {starting ? "启动中…" : "开始仿真"}
        </button>
        {status && (
          <span className={`sim-status sim-status--${status}`} role="status">
            {STATUS_LABEL[status]}
          </span>
        )}
      </div>

      {status === "error" && errorMessage && (
        <div className="sim-error" role="alert">
          {errorMessage}
        </div>
      )}

      {status === "running" && (
        <div className="sim-table-wrapper">
          {Object.keys(variables).length === 0 ? (
            <p className="sim-empty">暂无变量数据</p>
          ) : (
            <table className="sim-table" aria-label="变量状态">
              <thead>
                <tr>
                  <th>变量名</th>
                  <th>当前值</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(variables).map(([name, value]) => (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>{String(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function formatError(msg: string): string {
  if (!msg || msg.includes("无法连接") || msg.includes("超时")) {
    return "仿真器无法连接，请确认 Docker 已启动";
  }
  return msg;
}
