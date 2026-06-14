"""Tests for ST and SCL exporters (Issue 07)."""

from __future__ import annotations

import pytest

from plc_logic_gen.exporters import export_scl, export_st
from plc_logic_gen.models.ld import (
    Coil,
    Contact,
    ContactType,
    DataType,
    PLCProgram,
    Rung,
    Variable,
)


def _make_program() -> PLCProgram:
    return PLCProgram(
        title="Motor Control",
        description="Basic motor start/stop logic",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="stop_btn", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
            Variable(name="delay_time", data_type=DataType.TIME, initial_value="T#2s"),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="start_btn"),
                    Contact(type=ContactType.NC, variable="stop_btn"),
                    Coil(variable="motor_run"),
                ],
                comment="Motor start/stop logic",
            )
        ],
        st_code=(
            "IF start_btn AND NOT stop_btn THEN\n"
            "  motor_run := TRUE;\n"
            "ELSE\n"
            "  motor_run := FALSE;\n"
            "END_IF"
        ),
    )


# ---------------------------------------------------------------------------
# ST 导出器
# ---------------------------------------------------------------------------

class TestExportST:
    def test_returns_string(self):
        result = export_st(_make_program())
        assert isinstance(result, str)

    def test_contains_var_block(self):
        result = export_st(_make_program())
        assert "VAR" in result
        assert "END_VAR" in result

    def test_var_block_contains_variables(self):
        result = export_st(_make_program())
        assert "start_btn" in result
        assert "stop_btn" in result
        assert "motor_run" in result
        assert "delay_time" in result

    def test_var_block_contains_data_types(self):
        result = export_st(_make_program())
        assert "BOOL" in result
        assert "TIME" in result

    def test_var_initial_value_included(self):
        result = export_st(_make_program())
        assert "T#2s" in result

    def test_contains_st_code_body(self):
        result = export_st(_make_program())
        assert "motor_run := TRUE" in result
        assert "END_IF" in result

    def test_contains_program_title(self):
        result = export_st(_make_program())
        assert "Motor Control" in result

    def test_var_block_before_logic_body(self):
        result = export_st(_make_program())
        var_pos = result.index("VAR")
        body_pos = result.index("motor_run := TRUE")
        assert var_pos < body_pos

    def test_empty_variables_produces_empty_var_block(self):
        program = PLCProgram(
            title="Empty",
            rungs=[
                Rung(elements=[
                    Contact(type=ContactType.NO, variable="x"),
                    Coil(variable="y"),
                ])
            ],
            st_code="y := x;",
        )
        result = export_st(program)
        assert "VAR" in result
        assert "END_VAR" in result
        assert "y := x;" in result


# ---------------------------------------------------------------------------
# SCL 导出器
# ---------------------------------------------------------------------------

class TestExportSCL:
    def test_returns_string(self):
        result = export_scl(_make_program())
        assert isinstance(result, str)

    def test_contains_function_block_keyword(self):
        result = export_scl(_make_program())
        assert "FUNCTION_BLOCK" in result

    def test_contains_end_function_block(self):
        result = export_scl(_make_program())
        assert "END_FUNCTION_BLOCK" in result

    def test_contains_begin_section(self):
        result = export_scl(_make_program())
        assert "BEGIN" in result

    def test_contains_header_comment(self):
        result = export_scl(_make_program())
        assert "TIA Portal" in result

    def test_header_contains_version(self):
        result = export_scl(_make_program())
        assert "Version" in result or "version" in result

    def test_header_contains_author(self):
        result = export_scl(_make_program())
        assert "Author" in result or "author" in result

    def test_contains_program_title(self):
        result = export_scl(_make_program())
        assert "Motor_Control" in result or "Motor Control" in result

    def test_contains_var_block(self):
        result = export_scl(_make_program())
        assert "VAR" in result
        assert "END_VAR" in result

    def test_contains_st_code_body(self):
        result = export_scl(_make_program())
        assert "motor_run := TRUE" in result
        assert "END_IF" in result

    def test_function_block_wraps_begin(self):
        """FUNCTION_BLOCK 声明必须在 BEGIN 之前。"""
        result = export_scl(_make_program())
        fb_pos = result.index("FUNCTION_BLOCK")
        begin_pos = result.index("BEGIN")
        assert fb_pos < begin_pos

    def test_begin_before_logic_body(self):
        result = export_scl(_make_program())
        begin_pos = result.index("BEGIN")
        body_pos = result.index("motor_run := TRUE")
        assert begin_pos < body_pos


# ---------------------------------------------------------------------------
# 两个导出器输入相同程序时，逻辑体内容一致
# ---------------------------------------------------------------------------

class TestLogicBodyConsistency:
    def test_st_code_body_identical_in_both(self):
        program = _make_program()
        st_result = export_st(program)
        scl_result = export_scl(program)
        # 核心 ST 代码在两个输出中均存在
        for line in program.st_code.splitlines():
            stripped = line.strip()
            if stripped:
                assert stripped in st_result
                assert stripped in scl_result

    def test_variables_present_in_both(self):
        program = _make_program()
        st_result = export_st(program)
        scl_result = export_scl(program)
        for var in program.variables:
            assert var.name in st_result
            assert var.name in scl_result
