"""FastAPI application exposing /api/generate, /api/validate, /api/export, /api/simulate and /api/chat endpoints."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Literal

import anthropic
import openai
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, field_validator

from plc_logic_gen.exporter_excel import export_io_excel
from plc_logic_gen.exporter_l5x import export_l5x
from plc_logic_gen.exporters import export_scl, export_st
from plc_logic_gen.generator import GenerationError, generate_plc_program
from plc_logic_gen.io_extractor import IOExtractError, IOSignalList, extract_io_signals
from plc_logic_gen.models.ld import IOSignal, PLCProgram
from plc_logic_gen.openplc_client import SimulationError, SimulationResult, run_simulation
from plc_logic_gen.renderer import render_svg
from plc_logic_gen.sim_task_store import SimTaskStore
from plc_logic_gen.validator import LDError, validate_program

load_dotenv()

app = FastAPI(title="PLC Logic Generator API", version="0.1.0")

_CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

_LLM_MODEL_MAP: dict[str, str] = {
    "claude": f"anthropic:{os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-6')}",
    "openai": f"openai:{os.getenv('OPENAI_MODEL', 'gpt-4o')}",
}


class GenerateRequest(BaseModel):
    description: str
    brand: Literal["generic", "siemens", "rockwell"] = "generic"
    llm: Literal["claude", "openai"] = "claude"
    io_signals: list[IOSignal] = []


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


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
        description = request.description
        if request.io_signals:
            io_lines = []
            for sig in request.io_signals:
                dtype = "BOOL" if sig.signal_type.value in ("DI", "DO") else "REAL"
                line = f"- {sig.tag} ({sig.signal_type.value}) {sig.name} → {dtype}"
                if sig.engineering_unit:
                    line += f" [{sig.range_low}~{sig.range_high} {sig.engineering_unit}]"
                io_lines.append(line)
            io_block = "I/O Table (use these tag names as variable names):\n" + "\n".join(io_lines)
            description = description + "\n\n" + io_block
        result = generate_plc_program(description, request.brand, model_name)
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

_sim_store = SimTaskStore()


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
    _sim_store.create(task_id)
    background_tasks.add_task(_run_simulate_task_sync, task_id, request.st_code)
    return SimulateResponse(task_id=task_id)


@app.get("/api/simulate/{task_id}/status", response_model=SimulateStatusResponse)
def simulate_status(task_id: str):
    task = _sim_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task_id '{task_id}' 不存在。")
    return SimulateStatusResponse(
        status=task.status,
        variables=task.variables,
        error_message=task.error_message,
    )


def _run_simulate_task_sync(task_id: str, st_code: str) -> None:
    result = asyncio.run(run_simulation(st_code))
    if isinstance(result, SimulationError):
        _sim_store.finish_error(task_id, result.message)
    else:
        assert isinstance(result, SimulationResult)
        _sim_store.finish_ok(task_id, result.variables)


async def _run_simulate_task(task_id: str, st_code: str) -> None:
    """异步后台任务接口（供测试直接调用）。"""
    result = await run_simulation(st_code)
    if isinstance(result, SimulationError):
        _sim_store.finish_error(task_id, result.message)
    else:
        assert isinstance(result, SimulationResult)
        _sim_store.finish_ok(task_id, result.variables)


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# I/O 表端点
# ---------------------------------------------------------------------------

class IOTableExportRequest(BaseModel):
    signals: list[IOSignal]


@app.post("/api/io-table/export-excel")
def io_table_export_excel(request: IOTableExportRequest):
    content = export_io_excel(request.signals)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="io_table.xlsx"'},
    )


class IOTableGenerateRequest(BaseModel):
    messages: list[ChatMessage]
    llm: Literal["claude", "openai"] = "claude"


@app.post("/api/io-table/generate")
def io_table_generate(request: IOTableGenerateRequest):
    model_name = _LLM_MODEL_MAP[request.llm]
    messages_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
    result = extract_io_signals(messages_dicts, model_name)
    if isinstance(result, IOExtractError):
        return JSONResponse(status_code=422, content={"error": result.message})
    return {"signals": [s.model_dump() for s in result.signals]}


# ---------------------------------------------------------------------------
# FDS 生成端点
# ---------------------------------------------------------------------------

_FDS_SYSTEM_PROMPT = """\
你是一位资深 PLC 工程师，精通 IEC 61131-3 标准。根据用户提供的对话历史和 I/O 信号清单，\
生成一份结构化的功能规格说明书（Functional Design Specification，FDS）。

请严格按照以下章节结构输出 Markdown 格式的 FDS 文档：

# 功能规格说明书（FDS）

## 1. 项目概述
描述项目背景、目标和范围。

## 2. 控制目标
列出系统需要实现的控制目标和功能要求。

## 3. I/O 清单摘要
以表格形式列出所有 I/O 信号（Tag、名称、类型、说明）。

## 4. 控制逻辑描述
详细描述各工段的控制逻辑，包括启动/停止条件、时序逻辑。

## 5. 安全联锁要求
列出所有安全联锁条件和紧急停止逻辑。

## 6. 操作模式说明
描述系统的各种操作模式（手动/自动/维护等）及切换条件。

使用中文输出，语言专业规范。
"""


class FDSGenerateRequest(BaseModel):
    messages: list[ChatMessage]
    io_signals: list[IOSignal] = []
    llm: Literal["claude", "openai"] = "claude"

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages 不能为空")
        return v


async def _fds_iter_claude(messages_payload: list[dict], model_name: str) -> AsyncGenerator[str, None]:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    async with client.messages.stream(
        model=model_name,
        max_tokens=4096,
        system=_FDS_SYSTEM_PROMPT,
        messages=messages_payload,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _fds_iter_openai(messages_payload: list[dict], model_name: str) -> AsyncGenerator[str, None]:
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    stream = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": _FDS_SYSTEM_PROMPT}] + messages_payload,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        content = delta.content if delta is not None else None
        if content:
            yield content


@app.post("/api/fds/generate")
async def fds_generate(request: FDSGenerateRequest):
    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.io_signals:
        io_summary_lines = []
        for sig in request.io_signals:
            line = f"- {sig.tag} ({sig.signal_type.value}) {sig.name}"
            if sig.engineering_unit:
                line += f" [{sig.range_low}~{sig.range_high} {sig.engineering_unit}]"
            io_summary_lines.append(line)
        io_summary = "当前 I/O 信号清单：\n" + "\n".join(io_summary_lines)
        messages_payload[-1] = {
            "role": messages_payload[-1]["role"],
            "content": messages_payload[-1]["content"] + f"\n\n{io_summary}",
        }

    model_name = _LLM_MODEL_MAP[request.llm]
    iter_fn = _fds_iter_claude if request.llm == "claude" else _fds_iter_openai

    async def sse_stream() -> AsyncGenerator[str, None]:
        try:
            async for text in iter_fn(messages_payload, model_name):
                yield f"data: {json.dumps({'delta': text}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# AI 对话端点
# ---------------------------------------------------------------------------

_CHAT_SYSTEM_PROMPT = """\
你是一位拥有 20 年以上经验的资深 PLC 工程师，精通 IEC 61131-3 标准，熟悉西门子、罗克韦尔、施耐德等主流品牌。\
你的任务是通过对话帮助用户梳理 PLC 控制逻辑需求。

规则：
1. 始终使用中文回复。
2. 主动追问需求细节，每次最多追问 2-3 个问题，聚焦于：传感器信号与类型、执行器与动作、时序逻辑（延时、顺序）、保护/联锁条件、故障处理。
3. 当需求已足够清晰时（包含输入信号、输出控制、核心逻辑、保护条件），在回复末尾输出如下格式的需求摘要块（需求不清晰时不要输出）：

---SUMMARY---
<整理好的需求描述，可直接粘贴到生成框>
---END---
"""


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    description: str = ""
    st_code: str = ""
    llm: Literal["claude", "openai"] = "claude"

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages 不能为空")
        return v


async def _chat_iter_claude(messages_payload: list[dict], model_name: str) -> AsyncGenerator[str, None]:
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    async with client.messages.stream(
        model=model_name,
        max_tokens=2048,
        system=_CHAT_SYSTEM_PROMPT,
        messages=messages_payload,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _chat_iter_openai(messages_payload: list[dict], model_name: str) -> AsyncGenerator[str, None]:
    import traceback as _tb
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    stream = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": _CHAT_SYSTEM_PROMPT}] + messages_payload,
        stream=True,
    )
    try:
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content if delta is not None else None
            if content:
                yield content
    except Exception as _e:
        print(f"[chat_openai] stream error: {_e}\n{_tb.format_exc()}")
        raise


_MAX_CHAT_HISTORY = 40


@app.post("/api/chat")
async def chat(request: ChatRequest):
    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

    # 截断过长历史，防止 context window 溢出；确保截断后首条仍为 user
    if len(messages_payload) > _MAX_CHAT_HISTORY:
        messages_payload = messages_payload[-_MAX_CHAT_HISTORY:]
        while messages_payload and messages_payload[0]["role"] != "user":
            messages_payload.pop(0)

    # 将上下文注入最后一条消息（当前用户输入），而非历史首条
    context_parts: list[str] = []
    if request.description:
        context_parts.append(f"[当前用户已填写的描述：{request.description}]")
    if request.st_code:
        context_parts.append(f"[当前已生成的 ST 代码：\n```\n{request.st_code}\n```\n]")
    if context_parts and messages_payload:
        last = messages_payload[-1]
        messages_payload[-1] = {
            "role": last["role"],
            "content": last["content"] + "\n\n" + "\n".join(context_parts),
        }

    model_name = _LLM_MODEL_MAP[request.llm]
    iter_fn = _chat_iter_claude if request.llm == "claude" else _chat_iter_openai

    async def sse_stream() -> AsyncGenerator[str, None]:
        try:
            async for text in iter_fn(messages_payload, model_name):
                yield f"data: {json.dumps({'delta': text}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
