"""FastAPI application exposing /api/generate, /api/validate, /api/export and /api/simulate endpoints."""

from __future__ import annotations

import asyncio
import os
import threading
import uuid
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from plc_logic_gen.exporter_l5x import export_l5x
from plc_logic_gen.exporters import export_scl, export_st
from plc_logic_gen.generator import GenerationError, generate_plc_program
from plc_logic_gen.models.ld import PLCProgram
from plc_logic_gen.openplc_client import SimulationError, SimulationResult, run_simulation
from plc_logic_gen.renderer import render_svg
from plc_logic_gen.validator import LDError, validate_program

load_dotenv()

app = FastAPI(title="PLC Logic Generator API", version="0.1.0")

_CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

_LLM_MODEL_MAP: dict[str, str] = {
    "claude": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
}


class GenerateRequest(BaseModel):
    description: str
    brand: Literal["generic", "siemens", "rockwell"] = "generic"
    llm: Literal["claude", "openai"] = "claude"


class GenerateResponse(BaseModel):
    plc_program: PLCProgram
    svg: str


class ValidateRequest(BaseModel):
    plc_program: PLCProgram


class ValidationErrorSchema(BaseModel):
    rule: str
    message: str
    context: dict[str, Any] = {}


class ValidateResponse(BaseModel):
    errors: list[ValidationErrorSchema]


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    try:
        model_name = _LLM_MODEL_MAP[request.llm]
        result = generate_plc_program(request.description, request.brand, model_name)
        if isinstance(result, GenerationError):
            return JSONResponse(status_code=422, content={"error": result.message})
        svg = render_svg(result)
        return GenerateResponse(plc_program=result, svg=svg)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        print(f"[generate] UNHANDLED EXCEPTION:\n{tb}")
        return JSONResponse(status_code=500, content={"error": str(exc), "traceback": tb})


@app.post("/api/validate", response_model=ValidateResponse)
def validate(request: ValidateRequest):
    errors: list[LDError] = validate_program(request.plc_program)
    return ValidateResponse(
        errors=[
            ValidationErrorSchema(rule=e.rule, message=e.message, context=e.context)
            for e in errors
        ]
    )


class ExportRequest(BaseModel):
    plc_program: PLCProgram
    brand: Literal["generic", "siemens", "rockwell"] = "generic"


_EXPORT_CONFIG: dict[str, tuple[str, str, str]] = {
    "generic":  ("st",  "text/plain",               export_st),   # type: ignore[dict-item]
    "siemens":  ("scl", "text/plain",               export_scl),  # type: ignore[dict-item]
    "rockwell": ("L5X", "application/xml",          export_l5x),  # type: ignore[dict-item]
}


@app.post("/api/export")
def export(request: ExportRequest):
    ext, media_type, exporter = _EXPORT_CONFIG[request.brand]
    content = exporter(request.plc_program)
    filename = f"{request.plc_program.title.replace(' ', '_')}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 渲染端点（用于 Demo 场景加载，不调用 LLM）
# ---------------------------------------------------------------------------

class RenderRequest(BaseModel):
    plc_program: PLCProgram


class RenderResponse(BaseModel):
    svg: str


@app.post("/api/render", response_model=RenderResponse)
def render_program(request: RenderRequest):
    svg = render_svg(request.plc_program)
    return RenderResponse(svg=svg)


# ---------------------------------------------------------------------------
# 仿真端点
# ---------------------------------------------------------------------------

# 内存中的任务状态存储；生产环境可替换为 Redis 等持久化方案
_simulate_tasks: dict[str, dict[str, Any]] = {}
_tasks_lock = threading.Lock()


class SimulateRequest(BaseModel):
    st_code: str


class SimulateResponse(BaseModel):
    task_id: str


class SimulateStatusResponse(BaseModel):
    status: Literal["compiling", "running", "error"]
    variables: dict[str, Any] = {}
    error_message: str | None = None


@app.post("/api/simulate", response_model=SimulateResponse)
def simulate(request: SimulateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    with _tasks_lock:
        _simulate_tasks[task_id] = {"status": "compiling", "variables": {}, "error_message": None}
    background_tasks.add_task(_run_simulate_task_sync, task_id, request.st_code)
    return SimulateResponse(task_id=task_id)


@app.get("/api/simulate/{task_id}/status", response_model=SimulateStatusResponse)
def simulate_status(task_id: str):
    with _tasks_lock:
        task = _simulate_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task_id '{task_id}' 不存在。")
    return SimulateStatusResponse(
        status=task["status"],
        variables=task["variables"],
        error_message=task["error_message"],
    )


def _run_simulate_task_sync(task_id: str, st_code: str) -> None:
    """同步后台任务：在新事件循环中运行仿真，更新任务状态。"""
    result = asyncio.run(run_simulation(st_code))
    with _tasks_lock:
        if isinstance(result, SimulationError):
            _simulate_tasks[task_id] = {
                "status": "error",
                "variables": {},
                "error_message": result.message,
            }
        else:
            assert isinstance(result, SimulationResult)
            _simulate_tasks[task_id] = {
                "status": "running",
                "variables": result.variables,
                "error_message": None,
            }


async def _run_simulate_task(task_id: str, st_code: str) -> None:
    """异步后台任务接口（供测试直接调用）。"""
    result = await run_simulation(st_code)
    with _tasks_lock:
        if isinstance(result, SimulationError):
            _simulate_tasks[task_id] = {
                "status": "error",
                "variables": {},
                "error_message": result.message,
            }
        else:
            assert isinstance(result, SimulationResult)
            _simulate_tasks[task_id] = {
                "status": "running",
                "variables": result.variables,
                "error_message": None,
            }


@app.get("/health")
def health():
    return {"status": "ok"}
