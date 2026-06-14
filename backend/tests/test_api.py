"""Tests for FastAPI endpoints: /api/generate and /api/validate."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from plc_logic_gen.api import app
from plc_logic_gen.generator import GenerationError
from plc_logic_gen.models.ld import (
    Coil,
    Contact,
    ContactType,
    DataType,
    PLCProgram,
    Rung,
    Variable,
)

client = TestClient(app)


def _make_valid_program() -> PLCProgram:
    return PLCProgram(
        title="Motor Start",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(elements=[
                Contact(type=ContactType.NO, variable="start_btn"),
                Coil(variable="motor_run"),
            ])
        ],
    )


# ── /api/generate ──────────────────────────────────────────────────────────────

def test_generate_valid_description_returns_program_and_svg():
    program = _make_valid_program()
    with patch("plc_logic_gen.api.generate_plc_program", return_value=program):
        resp = client.post("/api/generate", json={
            "description": "Start motor when start button is pressed",
            "brand": "generic",
            "llm": "claude",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "plc_program" in data
    assert "svg" in data
    assert data["svg"].startswith("<svg")


def test_generate_vague_description_returns_error():
    err = GenerationError(
        code="insufficient_description",
        message="Description is too vague. Specify variables, conditions, and actions.",
    )
    with patch("plc_logic_gen.api.generate_plc_program", return_value=err):
        resp = client.post("/api/generate", json={
            "description": "do something",
            "brand": "generic",
            "llm": "claude",
        })
    assert resp.status_code == 422
    assert "error" in resp.json()
    assert resp.json()["error"] == err.message


def test_generate_passes_brand_and_model_to_generator():
    program = _make_valid_program()
    with patch("plc_logic_gen.api.generate_plc_program", return_value=program) as mock_gen:
        client.post("/api/generate", json={
            "description": "Move conveyor belt",
            "brand": "siemens",
            "llm": "openai",
        })
    mock_gen.assert_called_once()
    _, kwargs_brand, kwargs_model = mock_gen.call_args.args
    assert kwargs_brand == "siemens"
    assert "gpt" in kwargs_model or kwargs_model == "gpt-4o"


# ── /api/validate ──────────────────────────────────────────────────────────────

def test_validate_valid_program_returns_empty_errors():
    program = _make_valid_program()
    resp = client.post("/api/validate", json={"plc_program": program.model_dump()})
    assert resp.status_code == 200
    assert resp.json()["errors"] == []


def test_validate_program_with_undeclared_variables_returns_errors():
    # Variables used in rungs but not declared in variables list
    program = PLCProgram(
        title="Bad Program",
        variables=[],
        rungs=[
            Rung(elements=[
                Contact(type=ContactType.NO, variable="start_btn"),
                Coil(variable="motor_run"),
            ])
        ],
    )
    resp = client.post("/api/validate", json={"plc_program": program.model_dump()})
    assert resp.status_code == 200
    errors = resp.json()["errors"]
    assert len(errors) >= 2
    rules = {e["rule"] for e in errors}
    assert "undeclared_variable" in rules


def test_validate_error_response_has_rule_and_message_fields():
    program = PLCProgram(
        title="Bad",
        variables=[],
        rungs=[Rung(elements=[
            Contact(type=ContactType.NO, variable="x"),
            Coil(variable="y"),
        ])],
    )
    resp = client.post("/api/validate", json={"plc_program": program.model_dump()})
    for err in resp.json()["errors"]:
        assert "rule" in err
        assert "message" in err


# ── infrastructure ─────────────────────────────────────────────────────────────

def test_swagger_ui_accessible():
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_cors_allows_local_frontend():
    resp = client.get("/docs", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ── /api/export ────────────────────────────────────────────────────────────────

def _export_body(brand: str) -> dict:
    return {"plc_program": _make_valid_program().model_dump(), "brand": brand}


def test_export_generic_returns_st_file():
    resp = client.post("/api/export", json=_export_body("generic"))
    assert resp.status_code == 200
    assert "VAR" in resp.text
    assert resp.headers["content-disposition"].endswith('.st"')


def test_export_siemens_returns_scl_file():
    resp = client.post("/api/export", json=_export_body("siemens"))
    assert resp.status_code == 200
    assert "FUNCTION_BLOCK" in resp.text
    assert resp.headers["content-disposition"].endswith('.scl"')


def test_export_rockwell_returns_l5x_file():
    resp = client.post("/api/export", json=_export_body("rockwell"))
    assert resp.status_code == 200
    assert "<Rung" in resp.text
    assert resp.headers["content-disposition"].endswith('.L5X"')


def test_export_filename_uses_program_title():
    resp = client.post("/api/export", json=_export_body("generic"))
    disposition = resp.headers["content-disposition"]
    assert "Motor_Start" in disposition


def test_export_content_disposition_is_attachment():
    resp = client.post("/api/export", json=_export_body("generic"))
    assert resp.headers["content-disposition"].startswith("attachment")


def test_export_st_content_contains_var_block():
    resp = client.post("/api/export", json=_export_body("generic"))
    assert "VAR" in resp.text
    assert "END_VAR" in resp.text


def test_export_scl_content_contains_function_block():
    resp = client.post("/api/export", json=_export_body("siemens"))
    assert "FUNCTION_BLOCK" in resp.text
    assert "END_FUNCTION_BLOCK" in resp.text


def test_export_l5x_content_is_valid_xml():
    import xml.etree.ElementTree as ET
    resp = client.post("/api/export", json=_export_body("rockwell"))
    tree = ET.fromstring(resp.text)
    assert tree.tag == "RSLogix5000Content"
