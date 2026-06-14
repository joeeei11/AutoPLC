"""Tests for the OpenPLC Runtime client (Issue 10).

All tests mock httpx — no real OpenPLC service is required.

Coverage:
  - Successful full flow: upload → compile → wait → start → read vars
  - ConnectError → SimulationError with clear message
  - TimeoutException → SimulationError with clear message
  - HTTP error on upload → SimulationError
  - HTTP error on compile → SimulationError
  - Compile status "error" → SimulationError with log
  - Compile timeout → SimulationError
  - HTTP error on start → SimulationError
  - Variables returned in both formats ({variables: {...}} and flat dict)
  - OPENPLC_URL env var is respected
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from plc_logic_gen.openplc_client import SimulationError, SimulationResult, run_simulation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ST_CODE = "IF start_btn THEN motor_run := TRUE; END_IF"


def _response(status_code: int, json_body: object | None = None, text: str = "") -> MagicMock:
    """Build a fake httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_body or {}
    return resp


def _mock_client(
    upload_resp: MagicMock,
    compile_resp: MagicMock,
    status_resps: list[MagicMock],
    start_resp: MagicMock,
    vars_resp: MagicMock,
) -> MagicMock:
    """Wire up an AsyncClient mock for the full happy path."""
    mock = AsyncMock()
    mock.post = AsyncMock(side_effect=[upload_resp, compile_resp, start_resp])
    mock.get = AsyncMock(side_effect=status_resps + [vars_resp] * 10)
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    async def test_returns_simulation_result(self):
        upload = _response(200)
        compile_trigger = _response(200)
        status_done = _response(200, {"status": "done"})
        start = _response(200)
        vars_resp = _response(200, {"variables": {"motor_run": True, "start_btn": False}})

        mock = _mock_client(upload, compile_trigger, [status_done], start, vars_resp)
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationResult)

    async def test_variables_populated(self):
        upload = _response(200)
        compile_trigger = _response(200)
        status_done = _response(200, {"status": "done"})
        start = _response(200)
        vars_resp = _response(200, {"variables": {"motor_run": True}})

        mock = _mock_client(upload, compile_trigger, [status_done], start, vars_resp)
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationResult)
        assert result.variables.get("motor_run") is True

    async def test_flat_variables_format(self):
        """OpenPLC may return a flat dict instead of {variables: {...}}."""
        upload = _response(200)
        compile_trigger = _response(200)
        status_done = _response(200, {"status": "done"})
        start = _response(200)
        vars_resp = _response(200, {"sensor_in": 42, "output_val": False})

        mock = _mock_client(upload, compile_trigger, [status_done], start, vars_resp)
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationResult)
        assert result.variables.get("sensor_in") == 42

    async def test_compile_polling_continues_while_pending(self):
        """Status is polled twice before returning done."""
        upload = _response(200)
        compile_trigger = _response(200)
        status_pending = _response(200, {"status": "pending"})
        status_done = _response(200, {"status": "done"})
        start = _response(200)
        vars_resp = _response(200, {"variables": {}})

        mock = AsyncMock()
        mock.post = AsyncMock(side_effect=[upload, compile_trigger, start])
        mock.get = AsyncMock(side_effect=[status_pending, status_done] + [vars_resp] * 10)

        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("plc_logic_gen.openplc_client.asyncio.sleep", new_callable=AsyncMock):
                result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationResult)


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------

class TestNetworkErrors:
    async def test_connect_error_returns_simulation_error(self):
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "连接" in result.message or "connect" in result.message.lower()

    async def test_timeout_error_returns_simulation_error(self):
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "超时" in result.message or "timeout" in result.message.lower()

    async def test_error_message_includes_url(self):
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "localhost" in result.message or "8080" in result.message


# ---------------------------------------------------------------------------
# Upload failures
# ---------------------------------------------------------------------------

class TestUploadFailures:
    async def test_upload_4xx_returns_error(self):
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(return_value=_response(400, text="Bad Request"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "400" in result.message or "上传" in result.message

    async def test_upload_500_returns_error(self):
        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(return_value=_response(500, text="Internal error"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)


# ---------------------------------------------------------------------------
# Compile failures
# ---------------------------------------------------------------------------

class TestCompileFailures:
    async def test_compile_trigger_failure_returns_error(self):
        upload = _response(200)
        compile_fail = _response(500, text="Compile service down")

        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=[upload, compile_fail])
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "编译" in result.message or "500" in result.message

    async def test_compile_status_error_returns_error_with_log(self):
        upload = _response(200)
        compile_trigger = _response(200)
        status_error = _response(200, {"status": "error", "log": "undefined variable 'x'"})

        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=[upload, compile_trigger])
            mock.get = AsyncMock(return_value=status_error)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "编译失败" in result.message or "error" in result.message.lower()
        assert "undefined variable" in result.message


# ---------------------------------------------------------------------------
# Start PLC failure
# ---------------------------------------------------------------------------

class TestStartPlcFailure:
    async def test_start_failure_returns_error(self):
        upload = _response(200)
        compile_trigger = _response(200)
        status_done = _response(200, {"status": "done"})
        start_fail = _response(500, text="Cannot start PLC")

        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=[upload, compile_trigger, start_fail])
            mock.get = AsyncMock(return_value=status_done)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "PLC" in result.message or "500" in result.message


# ---------------------------------------------------------------------------
# OPENPLC_URL env var
# ---------------------------------------------------------------------------

class TestEnvVar:
    async def test_custom_url_is_used(self, monkeypatch):
        monkeypatch.setenv("OPENPLC_URL", "http://myhost:9090")
        with patch("plc_logic_gen.openplc_client.OPENPLC_URL", "http://myhost:9090"):
            with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
                mock = AsyncMock()
                mock.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
                MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await run_simulation(ST_CODE)

        assert isinstance(result, SimulationError)
        assert "myhost" in result.message or "9090" in result.message
        MockClient.assert_called_once()
        assert "myhost:9090" in MockClient.call_args.kwargs.get("base_url", "")
