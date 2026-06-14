"""OpenPLC Runtime REST 客户端。

客户端流程：
  1. 上传 .st 文件（POST /upload-program）
  2. 触发编译（POST /compile-program）
  3. 轮询等待编译完成（GET /compile-status）
  4. 启动 PLC（POST /start-plc）
  5. 轮询读取变量状态（GET /runtime-vars）
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

OPENPLC_URL: str = os.getenv("OPENPLC_URL", "http://localhost:8080")

# 轮询间隔（秒）
_COMPILE_POLL_INTERVAL = 1.0
_COMPILE_TIMEOUT = 60.0  # 最多等待编译 60 秒
_RUN_POLL_INTERVAL = 0.5
_RUN_POLL_COUNT = 4       # 读取几轮变量就返回


@dataclass
class SimulationResult:
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationError:
    message: str


async def run_simulation(st_code: str) -> SimulationResult | SimulationError:
    """执行完整仿真流程，返回变量快照或错误。"""
    base_url = OPENPLC_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            # 1. 上传程序
            upload_result = await _upload_program(client, st_code)
            if isinstance(upload_result, SimulationError):
                return upload_result

            # 2. 触发编译
            compile_result = await _compile_program(client)
            if isinstance(compile_result, SimulationError):
                return compile_result

            # 3. 等待编译完成
            wait_result = await _wait_for_compile(client)
            if isinstance(wait_result, SimulationError):
                return wait_result

            # 4. 启动 PLC
            start_result = await _start_plc(client)
            if isinstance(start_result, SimulationError):
                return start_result

            # 5. 读取变量
            return await _read_variables(client)

    except httpx.ConnectError:
        return SimulationError(
            message=f"无法连接到 OpenPLC Runtime（{base_url}），请确认服务已启动。"
        )
    except httpx.TimeoutException:
        return SimulationError(message=f"连接 OpenPLC Runtime 超时（{base_url}）。")
    except Exception as exc:  # noqa: BLE001
        return SimulationError(message=f"仿真过程发生意外错误：{exc}")


async def _upload_program(client: httpx.AsyncClient, st_code: str) -> None | SimulationError:
    """上传 .st 源码到 OpenPLC。"""
    files = {"file": ("program.st", st_code.encode(), "text/plain")}
    resp = await client.post("/upload-program", files=files)
    if resp.status_code not in (200, 201):
        return SimulationError(
            message=f"上传程序失败，HTTP {resp.status_code}：{resp.text[:200]}"
        )
    return None


async def _compile_program(client: httpx.AsyncClient) -> None | SimulationError:
    """触发编译。"""
    resp = await client.post("/compile-program")
    if resp.status_code not in (200, 202):
        return SimulationError(
            message=f"触发编译失败，HTTP {resp.status_code}：{resp.text[:200]}"
        )
    return None


async def _wait_for_compile(client: httpx.AsyncClient) -> None | SimulationError:
    """轮询 /compile-status 直到编译完成。"""
    deadline = asyncio.get_event_loop().time() + _COMPILE_TIMEOUT
    while True:
        resp = await client.get("/compile-status")
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "")
            if status == "done":
                return None
            if status == "error":
                log = data.get("log", "")
                return SimulationError(message=f"编译失败：{log[:500]}")
        # 超时
        if asyncio.get_event_loop().time() >= deadline:
            return SimulationError(message="等待编译超时（60 秒）。")
        await asyncio.sleep(_COMPILE_POLL_INTERVAL)


async def _start_plc(client: httpx.AsyncClient) -> None | SimulationError:
    """启动 PLC Runtime。"""
    resp = await client.post("/start-plc")
    if resp.status_code not in (200, 202):
        return SimulationError(
            message=f"启动 PLC 失败，HTTP {resp.status_code}：{resp.text[:200]}"
        )
    return None


async def _read_variables(client: httpx.AsyncClient) -> SimulationResult | SimulationError:
    """轮询几次 /runtime-vars，返回最新一次的变量快照。"""
    last_vars: dict[str, Any] = {}
    for _ in range(_RUN_POLL_COUNT):
        await asyncio.sleep(_RUN_POLL_INTERVAL)
        resp = await client.get("/runtime-vars")
        if resp.status_code == 200:
            data = resp.json()
            # 兼容 {"variables": {...}} 和直接返回 {...}
            if isinstance(data, dict) and "variables" in data:
                last_vars = data["variables"]
            elif isinstance(data, dict):
                last_vars = data
    return SimulationResult(variables=last_vars)
