"""Tests for POST /api/simulate and GET /api/simulate/{task_id}/status.

Coverage:
  - POST /api/simulate returns task_id
  - GET /api/simulate/{task_id}/status returns compiling initially
  - After successful simulation, status becomes running with variables
  - After failed simulation, status becomes error with error_message
  - Unknown task_id returns 404
  - OPENPLC_URL unavailable → status error with clear message
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from plc_logic_gen.api import app
from plc_logic_gen.openplc_client import SimulationError, SimulationResult

client = TestClient(app)

ST_CODE = "IF start_btn THEN motor_run := TRUE; END_IF"


# ---------------------------------------------------------------------------
# POST /api/simulate
# ---------------------------------------------------------------------------

class TestPostSimulate:
    def test_returns_task_id(self):
        with patch("plc_logic_gen.api._run_simulate_task_sync"):
            resp = client.post("/api/simulate", json={"st_code": ST_CODE})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    def test_task_id_is_unique_per_request(self):
        with patch("plc_logic_gen.api._run_simulate_task_sync"):
            r1 = client.post("/api/simulate", json={"st_code": ST_CODE})
            r2 = client.post("/api/simulate", json={"st_code": ST_CODE})
        assert r1.json()["task_id"] != r2.json()["task_id"]

    def test_empty_st_code_still_creates_task(self):
        """Validation is OpenPLC's job; the endpoint accepts any string."""
        with patch("plc_logic_gen.api._run_simulate_task_sync"):
            resp = client.post("/api/simulate", json={"st_code": ""})
        assert resp.status_code == 200
        assert "task_id" in resp.json()


# ---------------------------------------------------------------------------
# GET /api/simulate/{task_id}/status — unknown task
# ---------------------------------------------------------------------------

class TestSimulateStatusUnknown:
    def test_unknown_task_id_returns_404(self):
        resp = client.get("/api/simulate/nonexistent-id/status")
        assert resp.status_code == 404

    def test_404_body_mentions_task_id(self):
        resp = client.get("/api/simulate/some-bad-id/status")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/simulate/{task_id}/status — after background task completes
# ---------------------------------------------------------------------------

class TestSimulateStatusAfterRun:
    def test_status_running_after_success(self):
        """Inject a SimulationResult directly into the task store."""
        from plc_logic_gen.api import _simulate_tasks, _tasks_lock

        task_id = "test-success-id"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "running",
                "variables": {"motor_run": True},
                "error_message": None,
            }
        try:
            resp = client.get(f"/api/simulate/{task_id}/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "running"
            assert data["variables"]["motor_run"] is True
            assert data["error_message"] is None
        finally:
            with _tasks_lock:
                _simulate_tasks.pop(task_id, None)

    def test_status_error_after_failure(self):
        from plc_logic_gen.api import _simulate_tasks, _tasks_lock

        task_id = "test-error-id"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "error",
                "variables": {},
                "error_message": "无法连接到 OpenPLC Runtime",
            }
        try:
            resp = client.get(f"/api/simulate/{task_id}/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "error"
            assert data["variables"] == {}
            assert data["error_message"]
        finally:
            with _tasks_lock:
                _simulate_tasks.pop(task_id, None)

    def test_status_compiling_initially(self):
        from plc_logic_gen.api import _simulate_tasks, _tasks_lock

        task_id = "test-compiling-id"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "compiling",
                "variables": {},
                "error_message": None,
            }
        try:
            resp = client.get(f"/api/simulate/{task_id}/status")
            assert resp.status_code == 200
            assert resp.json()["status"] == "compiling"
        finally:
            with _tasks_lock:
                _simulate_tasks.pop(task_id, None)


# ---------------------------------------------------------------------------
# Background task integration: _run_simulate_task
# ---------------------------------------------------------------------------

class TestRunSimulateTask:
    async def test_run_simulate_task_sets_running_on_success(self):
        from plc_logic_gen.api import _run_simulate_task, _simulate_tasks, _tasks_lock

        task_id = "bg-success"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "compiling",
                "variables": {},
                "error_message": None,
            }
        mock_result = SimulationResult(variables={"out": True})
        with patch("plc_logic_gen.api.run_simulation", new_callable=AsyncMock, return_value=mock_result):
            await _run_simulate_task(task_id, ST_CODE)

        with _tasks_lock:
            task = _simulate_tasks[task_id]
        assert task["status"] == "running"
        assert task["variables"]["out"] is True
        assert task["error_message"] is None

    async def test_run_simulate_task_sets_error_on_failure(self):
        from plc_logic_gen.api import _run_simulate_task, _simulate_tasks, _tasks_lock

        task_id = "bg-error"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "compiling",
                "variables": {},
                "error_message": None,
            }
        mock_err = SimulationError(message="服务不可达")
        with patch("plc_logic_gen.api.run_simulation", new_callable=AsyncMock, return_value=mock_err):
            await _run_simulate_task(task_id, ST_CODE)

        with _tasks_lock:
            task = _simulate_tasks[task_id]
        assert task["status"] == "error"
        assert task["variables"] == {}
        assert "不可达" in task["error_message"]

    def test_openplc_unreachable_produces_error_status(self):
        """End-to-end via sync task runner: simulate → connect error → error status."""
        import httpx

        from plc_logic_gen.api import _run_simulate_task_sync, _simulate_tasks, _tasks_lock

        task_id = "unreachable-test"
        with _tasks_lock:
            _simulate_tasks[task_id] = {
                "status": "compiling",
                "variables": {},
                "error_message": None,
            }

        with patch("plc_logic_gen.openplc_client.httpx.AsyncClient") as MockClient:
            mock = AsyncMock()
            mock.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            _run_simulate_task_sync(task_id, ST_CODE)

        with _tasks_lock:
            task = _simulate_tasks[task_id]
        assert task["status"] == "error"
        assert task["error_message"]
