"""Tests for /api/io-table/generate endpoint (mock agent)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from plc_logic_gen.api import app
from plc_logic_gen.io_extractor import IOSignalList, IOExtractError, extract_io_signals
from plc_logic_gen.models.ld import IOSignal, SignalType


class TestExtractIOSignals:
    def test_mock_agent_returns_signal_list(self):
        mock_result = MagicMock()
        mock_result.output = IOSignalList(signals=[
            IOSignal(tag="DI_Motor_Start", name="启动按钮", signal_type=SignalType.DI),
            IOSignal(tag="AI_Temp_In", name="入口温度", signal_type=SignalType.AI,
                     range_low=0.0, range_high=200.0, engineering_unit="℃"),
        ])
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = mock_result

        result = extract_io_signals(
            [{"role": "user", "content": "电机启动按钮控制泵，有温度传感器"}],
            _agent=mock_agent,
        )
        assert isinstance(result, IOSignalList)
        assert len(result.signals) == 2
        assert result.signals[0].tag == "DI_Motor_Start"
        assert result.signals[1].signal_type == SignalType.AI

    def test_empty_messages_returns_error(self):
        result = extract_io_signals([])
        assert isinstance(result, IOExtractError)
        assert "No messages" in result.message

    def test_mock_agent_exception_returns_error(self):
        mock_agent = MagicMock()
        mock_agent.run_sync.side_effect = RuntimeError("LLM unavailable")
        result = extract_io_signals(
            [{"role": "user", "content": "test"}],
            _agent=mock_agent,
        )
        assert isinstance(result, IOExtractError)
        assert "LLM unavailable" in result.message


class TestIOTableGenerateEndpoint:
    def test_returns_422_on_empty_messages(self):
        client = TestClient(app)
        resp = client.post("/api/io-table/generate", json={"messages": []})
        # ChatRequest validator rejects empty messages
        assert resp.status_code in (422, 400)

    def test_endpoint_calls_extractor(self, monkeypatch):
        mock_signals = [
            IOSignal(tag="DI001", signal_type=SignalType.DI).model_dump()
        ]

        def fake_extract(messages, model_name, **kwargs):
            return IOSignalList(signals=[
                IOSignal(tag="DI001", signal_type=SignalType.DI)
            ])

        monkeypatch.setattr("plc_logic_gen.api.extract_io_signals", fake_extract)
        client = TestClient(app)
        resp = client.post("/api/io-table/generate", json={
            "messages": [{"role": "user", "content": "有一个启动按钮"}],
            "llm": "claude",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert data["signals"][0]["tag"] == "DI001"
