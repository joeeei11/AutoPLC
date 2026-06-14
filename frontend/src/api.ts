/** 与后端 FastAPI 交互的类型定义和请求函数 */

export type ContactType = "NO" | "NC";
export type Brand = "generic" | "siemens" | "rockwell";
export type LLM = "claude" | "openai";

export interface Contact {
  type: ContactType;
  variable: string;
}

export interface Coil {
  variable: string;
  negated: boolean;
}

export interface FunctionBlock {
  block_type: string;
  instance_name: string;
  inputs: Record<string, string>;
  outputs: Record<string, string>;
}

export type Element = Contact | Coil | FunctionBlock;

export interface Branch {
  paths: Element[][];
}

export interface Variable {
  name: string;
  data_type: string;
  initial_value?: string | null;
}

export interface Rung {
  elements: (Element | Branch)[];
}

export interface PLCProgram {
  title: string;
  description: string;
  variables: Variable[];
  rungs: Rung[];
  st_code: string;
}

export interface GenerateRequest {
  description: string;
  brand: Brand;
  llm: LLM;
}

export interface GenerateResponse {
  plc_program: PLCProgram;
  svg: string;
}

export interface GenerateErrorResponse {
  error: string;
}

export interface ValidationErrorItem {
  rule: string;
  message: string;
  context: Record<string, unknown>;
}

export interface ValidateResponse {
  errors: ValidationErrorItem[];
}

const BASE_URL = "";

export async function generatePLC(req: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch(`${BASE_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  const data = await res.json();

  if (!res.ok) {
    const msg = (data as GenerateErrorResponse).error ?? `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data as GenerateResponse;
}

export async function validatePLC(plcProgram: PLCProgram): Promise<ValidateResponse> {
  const res = await fetch(`${BASE_URL}/api/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plc_program: plcProgram }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json() as Promise<ValidateResponse>;
}

export type SimulationStatus = "compiling" | "running" | "error";

export interface SimulateStatusResponse {
  status: SimulationStatus;
  variables: Record<string, unknown>;
  error_message?: string | null;
}

export async function startSimulation(stCode: string): Promise<{ task_id: string }> {
  const res = await fetch(`${BASE_URL}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ st_code: stCode }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<{ task_id: string }>;
}

export async function getSimulationStatus(taskId: string): Promise<SimulateStatusResponse> {
  const res = await fetch(`${BASE_URL}/api/simulate/${encodeURIComponent(taskId)}/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<SimulateStatusResponse>;
}

export async function renderPLC(plcProgram: PLCProgram): Promise<{ svg: string }> {
  const res = await fetch(`${BASE_URL}/api/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plc_program: plcProgram }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<{ svg: string }>;
}

export async function exportPLC(plcProgram: PLCProgram, brand: Brand): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plc_program: plcProgram, brand }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  const disposition = res.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `export.${brand === "rockwell" ? "L5X" : brand === "siemens" ? "scl" : "st"}`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
