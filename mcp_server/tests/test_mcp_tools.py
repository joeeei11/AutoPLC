"""MCP Server 工具函数测试（通过 mock httpx 隔离后端依赖）。"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data=None, content: bytes = b"", headers=None):
    """构造 httpx 响应 Mock。"""
    res = MagicMock()
    res.status_code = status_code
    res.json.return_value = json_data if json_data is not None else {}
    res.text = json.dumps(json_data) if json_data is not None else ""
    res.content = content
    res.headers = headers or {"content-type": "application/json"}
    return res


def _mock_client(post_res=None, get_res=None):
    """构造 httpx.Client 上下文管理器 Mock。"""
    client = MagicMock()
    if post_res is not None:
        client.post.return_value = post_res
    if get_res is not None:
        client.get.return_value = get_res
    # 支持 with httpx.Client(...) as c:
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=client)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, client


# ---------------------------------------------------------------------------
# generate_plc_logic
# ---------------------------------------------------------------------------

class TestGeneratePlcLogic:
    def test_success_returns_json_with_svg(self):
        from server import generate_plc_logic

        payload = {"plc_program": {"title": "Test"}, "svg": "<svg></svg>"}
        mock_res = _mock_response(200, json_data=payload)
        mock_res.text = json.dumps(payload)
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = generate_plc_logic("电机启停")

        data = json.loads(result)
        assert "svg" in data
        assert data["svg"] == "<svg></svg>"

    def test_success_contains_plc_program(self):
        from server import generate_plc_logic

        payload = {"plc_program": {"title": "Motor"}, "svg": "<svg/>"}
        mock_res = _mock_response(200, json_data=payload)
        mock_res.text = json.dumps(payload)
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = generate_plc_logic("电机启停")

        data = json.loads(result)
        assert "plc_program" in data

    def test_backend_unreachable_returns_error(self):
        import httpx
        from server import generate_plc_logic

        with patch("server.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.side_effect = httpx.ConnectError("refused")
            result = generate_plc_logic("测试")

        data = json.loads(result)
        assert "error" in data
        assert "不可达" in data["error"]

    def test_http_error_returns_error(self):
        from server import generate_plc_logic

        mock_res = _mock_response(500, json_data={"error": "服务器内部错误"})
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = generate_plc_logic("测试")

        data = json.loads(result)
        assert "error" in data

    def test_passes_brand_and_llm(self):
        from server import generate_plc_logic

        payload = {"plc_program": {}, "svg": ""}
        mock_res = _mock_response(200, json_data=payload)
        mock_res.text = json.dumps(payload)
        ctx, client = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            generate_plc_logic("测试", brand="siemens", llm="openai")

        _, kwargs = client.post.call_args
        body = kwargs.get("json", {})
        assert body.get("brand") == "siemens"
        assert body.get("llm") == "openai"


# ---------------------------------------------------------------------------
# validate_plc_logic
# ---------------------------------------------------------------------------

class TestValidatePlcLogic:
    def test_valid_program_returns_empty_errors(self):
        from server import validate_plc_logic

        payload = {"errors": []}
        mock_res = _mock_response(200, json_data=payload)
        mock_res.text = json.dumps(payload)
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = validate_plc_logic(json.dumps({"title": "T", "rungs": []}))

        data = json.loads(result)
        assert data["errors"] == []

    def test_invalid_program_returns_errors(self):
        from server import validate_plc_logic

        errors = [{"rule": "coil_count", "message": "Rung 缺少 Coil", "context": {}}]
        payload = {"errors": errors}
        mock_res = _mock_response(200, json_data=payload)
        mock_res.text = json.dumps(payload)
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = validate_plc_logic(json.dumps({"title": "T"}))

        data = json.loads(result)
        assert len(data["errors"]) == 1

    def test_bad_json_input_returns_error(self):
        from server import validate_plc_logic

        result = validate_plc_logic("not-valid-json{{{")
        data = json.loads(result)
        assert "error" in data
        assert "JSON" in data["error"]

    def test_backend_unreachable_returns_error(self):
        import httpx
        from server import validate_plc_logic

        with patch("server.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.side_effect = httpx.ConnectError("refused")
            result = validate_plc_logic(json.dumps({"title": "T"}))

        data = json.loads(result)
        assert "error" in data

    def test_http_error_returns_error(self):
        from server import validate_plc_logic

        mock_res = _mock_response(422, json_data={})
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = validate_plc_logic(json.dumps({"title": "T"}))

        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# simulate_and_read
# ---------------------------------------------------------------------------

class TestSimulateAndRead:
    def test_running_returns_variables(self):
        from server import simulate_and_read

        start_res = _mock_response(200, {"task_id": "t1"})
        status_res = _mock_response(
            200, {"status": "running", "variables": {"motor_run": True}}
        )
        ctx_start, client_start = _mock_client(post_res=start_res)
        ctx_status, client_status = _mock_client(get_res=status_res)

        clients = [ctx_start, ctx_status]
        with patch("server.httpx.Client", side_effect=clients):
            result = simulate_and_read("motor_run := TRUE;")

        data = json.loads(result)
        assert "variables" in data
        assert data["variables"]["motor_run"] is True

    def test_error_status_returns_error_message(self):
        from server import simulate_and_read

        start_res = _mock_response(200, {"task_id": "t2"})
        status_res = _mock_response(
            200, {"status": "error", "error_message": "OpenPLC 无法连接"}
        )
        ctx_start, _ = _mock_client(post_res=start_res)
        ctx_status, _ = _mock_client(get_res=status_res)

        with patch("server.httpx.Client", side_effect=[ctx_start, ctx_status]):
            result = simulate_and_read("bad code")

        data = json.loads(result)
        assert "error" in data
        assert "OpenPLC" in data["error"]

    def test_backend_unreachable_at_start_returns_error(self):
        import httpx
        from server import simulate_and_read

        with patch("server.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.side_effect = httpx.ConnectError("refused")
            result = simulate_and_read("motor_run := TRUE;")

        data = json.loads(result)
        assert "error" in data
        assert "不可达" in data["error"]

    def test_start_http_error_returns_error(self):
        from server import simulate_and_read

        start_res = _mock_response(500, {})
        ctx, _ = _mock_client(post_res=start_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = simulate_and_read("motor_run := TRUE;")

        data = json.loads(result)
        assert "error" in data

    def test_timeout_returns_timeout_error(self):
        import time
        from server import simulate_and_read

        start_res = _mock_response(200, {"task_id": "t3"})
        # 每次 get 都返回 "compiling"
        status_res = _mock_response(200, {"status": "compiling"})

        ctx_start, _ = _mock_client(post_res=start_res)

        call_count = 0

        def client_factory(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ctx_start
            ctx, _ = _mock_client(get_res=status_res)
            return ctx

        # 缩短超时以加速测试
        import server as srv_module
        original_timeout = srv_module._SIMULATE_TIMEOUT
        original_interval = srv_module._SIMULATE_POLL_INTERVAL
        srv_module._SIMULATE_TIMEOUT = 0.05   # 50ms
        srv_module._SIMULATE_POLL_INTERVAL = 0.01

        try:
            with patch("server.httpx.Client", side_effect=client_factory):
                result = simulate_and_read("motor_run := TRUE;")
        finally:
            srv_module._SIMULATE_TIMEOUT = original_timeout
            srv_module._SIMULATE_POLL_INTERVAL = original_interval

        data = json.loads(result)
        assert "error" in data
        assert "超时" in data["error"]

    def test_missing_task_id_returns_error(self):
        from server import simulate_and_read

        start_res = _mock_response(200, {"task_id": None})
        ctx, _ = _mock_client(post_res=start_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = simulate_and_read("motor_run := TRUE;")

        data = json.loads(result)
        assert "error" in data


# ---------------------------------------------------------------------------
# export_plc_file
# ---------------------------------------------------------------------------

class TestExportPlcFile:
    def _make_plc_json(self) -> str:
        return json.dumps({"title": "Motor", "rungs": [], "variables": []})

    def test_success_returns_filename_and_base64(self):
        from server import export_plc_file

        file_content = b"PROGRAM motor\nEND_PROGRAM"
        mock_res = _mock_response(
            200,
            content=file_content,
            headers={"content-disposition": 'attachment; filename="motor.st"'},
        )
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json())

        data = json.loads(result)
        assert data["filename"] == "motor.st"
        assert "content_base64" in data

    def test_base64_decodes_to_original_content(self):
        from server import export_plc_file

        file_content = b"PROGRAM motor\nEND_PROGRAM"
        mock_res = _mock_response(
            200,
            content=file_content,
            headers={"content-disposition": 'attachment; filename="motor.st"'},
        )
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json())

        data = json.loads(result)
        decoded = base64.b64decode(data["content_base64"])
        assert decoded == file_content

    def test_default_filename_for_generic_brand(self):
        from server import export_plc_file

        mock_res = _mock_response(
            200,
            content=b"content",
            headers={"content-disposition": ""},
        )
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json(), brand="generic")

        data = json.loads(result)
        assert data["filename"].endswith(".st")

    def test_default_filename_for_siemens_brand(self):
        from server import export_plc_file

        mock_res = _mock_response(200, content=b"content", headers={"content-disposition": ""})
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json(), brand="siemens")

        data = json.loads(result)
        assert data["filename"].endswith(".scl")

    def test_bad_json_input_returns_error(self):
        from server import export_plc_file

        result = export_plc_file("not-json{{{")
        data = json.loads(result)
        assert "error" in data

    def test_backend_unreachable_returns_error(self):
        import httpx
        from server import export_plc_file

        with patch("server.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.side_effect = httpx.ConnectError("refused")
            result = export_plc_file(self._make_plc_json())

        data = json.loads(result)
        assert "error" in data

    def test_http_error_returns_error(self):
        from server import export_plc_file

        mock_res = _mock_response(422, content=b"", headers={})
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json())

        data = json.loads(result)
        assert "error" in data

    def test_rockwell_default_extension(self):
        from server import export_plc_file

        mock_res = _mock_response(200, content=b"<RSLogix5000/>", headers={"content-disposition": ""})
        ctx, _ = _mock_client(post_res=mock_res)

        with patch("server.httpx.Client", return_value=ctx):
            result = export_plc_file(self._make_plc_json(), brand="rockwell")

        data = json.loads(result)
        assert data["filename"].endswith(".L5X")
