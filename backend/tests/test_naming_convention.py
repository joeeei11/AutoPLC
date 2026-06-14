"""Tests for naming_convention validator rule."""

from __future__ import annotations

import pytest

from plc_logic_gen.models.ld import (
    Coil, Contact, ContactType, DataType, PLCProgram, Rung, Variable,
)
from plc_logic_gen.validator import validate_program


def _prog(var_names: list[str]) -> PLCProgram:
    variables = [Variable(name=n, data_type=DataType.BOOL) for n in var_names]
    rungs = [Rung(elements=[
        Contact(type=ContactType.NO, variable=var_names[0]),
        Coil(variable=var_names[0]),
    ])] if var_names else []
    return PLCProgram(title="Test", variables=variables, rungs=rungs)


class TestNamingConvention:
    def test_compliant_names_no_warning(self):
        prog = _prog(["DI_Motor_Start"])
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert errors == []

    def test_noncompliant_lowercase_returns_warning(self):
        prog = _prog(["motor_run"])
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert len(errors) == 1
        assert "motor_run" in errors[0].message

    def test_noncompliant_missing_sections_returns_warning(self):
        prog = _prog(["DI_MotorStart"])
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert len(errors) == 1

    def test_warning_does_not_block_other_rules(self):
        prog = _prog(["motor_run"])
        errors = validate_program(prog)
        rules = {e.rule for e in errors}
        # naming_convention exists but no other blocking errors
        assert "naming_convention" in rules
        assert "undeclared_variable" not in rules

    def test_multiple_noncompliant_variables(self):
        prog = _prog(["start_btn", "stop_btn"])
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert len(errors) == 2

    def test_context_contains_variable_name(self):
        prog = _prog(["motor_run"])
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert errors[0].context["variable"] == "motor_run"

    def test_valid_prefix_variations(self):
        for name in ["DI_Pump_Run", "DO_Fan_Start", "AI_Temp_In", "AO_Speed_Set", "BOOL_Flag_Run"]:
            prog = _prog([name])
            errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
            assert errors == [], f"Expected no warning for {name}"

    def test_empty_variables_no_warning(self):
        prog = PLCProgram(title="Empty")
        errors = [e for e in validate_program(prog) if e.rule == "naming_convention"]
        assert errors == []
