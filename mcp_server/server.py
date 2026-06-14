#!/usr/bin/env python3
"""MCP Server for PLCLogicGen — 四个工具：generate / validate / simulate / export。"""

from __future__ import annotations

import base64
import json
import os
import time

import httpx
from mcp.server.fastmcp import FastMCP

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_SIMULATE_POLL_INTERVAL = 2.0
_SIMULATE_TIMEOUT = 60.0

mcp = FastMCP(
    "PLCLogicGen",
    instructions=(
        "PLC 逻辑生成工具集。"
        "先用 generate_plc_logic 生成程序，"
        "再用 validate_plc_logic 验证语义，"
        "可选 simulate_and_read 仿真或 export_plc_file 导出。"
    ),
)


@mcp.tool()
def generate_plc_logic(
    description: str,
    brand: str = "generic",
    llm: str = "claude",
) -> str:
    """根据自然语言描述生成 PLC 梯形图逻辑。

    返回 JSON 字符串，包含 plc_program（PLCProgram 对象）和 svg（SVG 字符串）。
    brand: generic | siemens | rockwell
    llm: claude | openai
    """
    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=120.0) as client:
            res = client.post(
                "/api/generate",
                json={"description": description, "brand": brand, "llm": llm},
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        return json.dumps({"error": f"后端服务不可达，请确认 {BACKEND_URL} 已启动"})

    if res.status_code != 200:
        try:
            err = res.json().get("error", f"HTTP {res.status_code}")
        except Exception:
            err = f"HTTP {res.status_code}"
        return json.dumps({"error": err})

    return res.text


@mcp.tool()
def validate_plc_logic(plc_program_json: str) -> str:
    """验证 PLCProgram JSON 的语义正确性。

    plc_program_json: PLCProgram 对象的 JSON 字符串。
    返回 JSON 字符串，包含 errors 列表（空列表表示合法）。
    """
    try:
        plc_program = json.loads(plc_program_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"无效的 JSON 输入: {exc}"})

    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=30.0) as client:
            res = client.post("/api/validate", json={"plc_program": plc_program})
    except (httpx.ConnectError, httpx.TimeoutException):
        return json.dumps({"error": f"后端服务不可达，请确认 {BACKEND_URL} 已启动"})

    if res.status_code != 200:
        return json.dumps({"error": f"HTTP {res.status_code}"})

    return res.text


@mcp.tool()
def simulate_and_read(st_code: str) -> str:
    """上传 ST 代码到 OpenPLC 仿真器，等待编译，读取变量状态。

    返回 JSON 字符串：{"variables": {...}} 或 {"error": "..."}。
    OpenPLC 不可达时立即返回错误，不挂起（最长等待 60 秒）。
    """
    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=30.0) as client:
            res = client.post("/api/simulate", json={"st_code": st_code})
    except (httpx.ConnectError, httpx.TimeoutException):
        return json.dumps({"error": f"后端服务不可达，请确认 {BACKEND_URL} 已启动"})

    if res.status_code != 200:
        return json.dumps({"error": f"启动仿真失败，HTTP {res.status_code}"})

    try:
        task_id = res.json().get("task_id")
    except Exception:
        return json.dumps({"error": "启动仿真返回无效响应"})

    if not task_id:
        return json.dumps({"error": "未获取到 task_id"})

    deadline = time.monotonic() + _SIMULATE_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with httpx.Client(base_url=BACKEND_URL, timeout=10.0) as client:
                status_res = client.get(f"/api/simulate/{task_id}/status")
        except (httpx.ConnectError, httpx.TimeoutException):
            return json.dumps({"error": "后端服务在轮询中断开连接"})

        if status_res.status_code != 200:
            return json.dumps({"error": f"轮询状态失败，HTTP {status_res.status_code}"})

        try:
            data = status_res.json()
        except Exception:
            return json.dumps({"error": "轮询返回无效响应"})

        status = data.get("status")
        if status == "running":
            return json.dumps({"variables": data.get("variables", {})}, ensure_ascii=False)
        if status == "error":
            msg = data.get("error_message") or "仿真出错"
            return json.dumps({"error": msg})

        time.sleep(_SIMULATE_POLL_INTERVAL)

    return json.dumps({"error": f"仿真超时（{_SIMULATE_TIMEOUT:.0f} 秒内未完成）"})


@mcp.tool()
def export_plc_file(plc_program_json: str, brand: str = "generic") -> str:
    """将 PLCProgram 导出为对应品牌格式的文件。

    plc_program_json: PLCProgram 对象的 JSON 字符串。
    brand: generic（.st）| siemens（.scl）| rockwell（.L5X）
    返回 JSON 字符串，包含 filename 和 content_base64（文件内容的 base64 编码）。
    """
    try:
        plc_program = json.loads(plc_program_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"error": f"无效的 JSON 输入: {exc}"})

    try:
        with httpx.Client(base_url=BACKEND_URL, timeout=30.0) as client:
            res = client.post("/api/export", json={"plc_program": plc_program, "brand": brand})
    except (httpx.ConnectError, httpx.TimeoutException):
        return json.dumps({"error": f"后端服务不可达，请确认 {BACKEND_URL} 已启动"})

    if res.status_code != 200:
        return json.dumps({"error": f"导出失败，HTTP {res.status_code}"})

    disposition = res.headers.get("content-disposition", "")
    filename = _parse_filename(disposition) or _default_filename(brand)

    content_b64 = base64.b64encode(res.content).decode("ascii")
    return json.dumps({"filename": filename, "content_base64": content_b64})


def _parse_filename(disposition: str) -> str | None:
    if 'filename="' in disposition:
        return disposition.split('filename="')[1].rstrip('"')
    if "filename=" in disposition:
        return disposition.split("filename=")[1].strip().strip('"')
    return None


def _default_filename(brand: str) -> str:
    ext_map = {"siemens": "scl", "rockwell": "L5X"}
    return f"export.{ext_map.get(brand, 'st')}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
