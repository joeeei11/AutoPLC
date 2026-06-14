"""Tests for the LD validator (Issue 02).

Rules under test:
  1 – all Contact/Coil variables must be declared in PLCProgram.variables
  2 – each Rung must have exactly one Coil output
  3 – every Branch path must contain at least one element
  4 – FunctionBlock.block_type must be a known FunctionBlockType

Rules 2-4 are already enforced by Pydantic model validators; tests here
use model_construct() to bypass Pydantic so the validator logic is tested
independently.
"""

import pytest
from plc_logic_gen.models.ld import (
    Branch,
    Coil,
    Contact,
    ContactType,
    DataType,
    FunctionBlock,
    FunctionBlockType,
    PLCProgram,
    Rung,
    Variable,
)
from plc_logic_gen.validator import LDError, validate_program


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _var(name: str) -> Variable:
    return Variable(name=name, data_type=DataType.BOOL)


def _no(var: str) -> Contact:
    return Contact(type=ContactType.NO, variable=var)


def _nc(var: str) -> Contact:
    return Contact(type=ContactType.NC, variable=var)


def _coil(var: str) -> Coil:
    return Coil(variable=var)


def _make_program(vars: list[str], rung_elements: list) -> PLCProgram:
    """Build a PLCProgram through normal Pydantic construction."""
    return PLCProgram(
        title="Test",
        variables=[_var(n) for n in vars],
        rungs=[Rung(elements=rung_elements)],
    )


def _make_program_bypass(
    vars: list[str], rungs: list[Rung]
) -> PLCProgram:
    """Build a PLCProgram bypassing Pydantic validators via model_construct."""
    return PLCProgram.model_construct(
        title="Test",
        description="",
        variables=[_var(n) for n in vars],
        rungs=rungs,
        st_code="",
    )


# ---------------------------------------------------------------------------
# Rule 1 – undeclared variables
# ---------------------------------------------------------------------------

class TestRule1UndeclaredVariables:
    def test_all_declared_returns_empty(self):
        prog = _make_program(["x", "y"], [_no("x"), _nc("y"), _coil("x")])
        assert validate_program(prog) == []

    def test_contact_undeclared_returns_error(self):
        prog = _make_program(["motor"], [_no("ghost"), _coil("motor")])
        errors = validate_program(prog)
        assert len(errors) == 1
        assert errors[0].rule == "undeclared_variable"
        assert "ghost" in errors[0].message

    def test_coil_undeclared_returns_error(self):
        prog = _make_program(["start"], [_no("start"), _coil("undeclared_out")])
        errors = validate_program(prog)
        assert any(e.rule == "undeclared_variable" and "undeclared_out" in e.message for e in errors)

    def test_multiple_undeclared_returns_multiple_errors(self):
        prog = _make_program([], [_no("a"), _coil("b")])
        errors = validate_program(prog)
        undeclared = [e for e in errors if e.rule == "undeclared_variable"]
        assert len(undeclared) == 2

    def test_undeclared_inside_branch_returns_error(self):
        prog = _make_program(
            ["motor"],
            [
                Branch(paths=[
                    [_no("declared_never")],
                    [_nc("motor")],
                ]),
                _coil("motor"),
            ],
        )
        errors = validate_program(prog)
        assert any(e.rule == "undeclared_variable" and "declared_never" in e.message for e in errors)

    def test_error_context_contains_variable_name(self):
        prog = _make_program(["out"], [_no("missing"), _coil("out")])
        errors = validate_program(prog)
        assert errors[0].context["variable"] == "missing"


# ---------------------------------------------------------------------------
# Rule 2 – Rung coil count
# ---------------------------------------------------------------------------

class TestRule2CoilCount:
    def test_single_coil_no_error(self):
        prog = _make_program(["x"], [_no("x"), _coil("x")])
        errors = [e for e in validate_program(prog) if e.rule == "coil_count"]
        assert errors == []

    def test_no_coil_returns_error(self):
        rung = Rung.model_construct(elements=[_no("x")], comment="")
        prog = _make_program_bypass(["x"], [rung])
        errors = validate_program(prog)
        assert any(e.rule == "coil_count" and "0" in e.message for e in errors)

    def test_two_coils_returns_error(self):
        rung = Rung.model_construct(elements=[_coil("a"), _coil("b")], comment="")
        prog = _make_program_bypass(["a", "b"], [rung])
        errors = validate_program(prog)
        assert any(e.rule == "coil_count" and "2" in e.message for e in errors)

    def test_coil_inside_branch_counts(self):
        # Branch with a coil counts as the single allowed coil
        prog = _make_program(
            ["a", "b"],
            [
                Branch(paths=[
                    [_no("a"), _coil("b")],
                    [_nc("a")],
                ]),
            ],
        )
        errors = [e for e in validate_program(prog) if e.rule == "coil_count"]
        assert errors == []


# ---------------------------------------------------------------------------
# Rule 3 – empty Branch paths
# ---------------------------------------------------------------------------

class TestRule3EmptyBranchPaths:
    def test_non_empty_paths_no_error(self):
        prog = _make_program(
            ["a", "b", "out"],
            [Branch(paths=[[_no("a")], [_nc("b")]]), _coil("out")],
        )
        errors = [e for e in validate_program(prog) if e.rule == "empty_branch_path"]
        assert errors == []

    def test_empty_path_inside_branch_returns_error(self):
        branch = Branch.model_construct(paths=[[], [_no("x")]])
        rung = Rung.model_construct(elements=[branch, _coil("x")], comment="")
        prog = _make_program_bypass(["x"], [rung])
        errors = validate_program(prog)
        assert any(e.rule == "empty_branch_path" for e in errors)

    def test_error_message_contains_path_index(self):
        branch = Branch.model_construct(paths=[[_no("x")], []])
        rung = Rung.model_construct(elements=[branch, _coil("x")], comment="")
        prog = _make_program_bypass(["x"], [rung])
        errors = [e for e in validate_program(prog) if e.rule == "empty_branch_path"]
        assert len(errors) == 1
        assert errors[0].context["path_index"] == 1


# ---------------------------------------------------------------------------
# Rule 4 – unknown FunctionBlock type
# ---------------------------------------------------------------------------

class TestRule4FunctionBlockType:
    def test_known_fb_type_no_error(self):
        fb = FunctionBlock(
            block_type=FunctionBlockType.TON,
            instance_name="t1",
        )
        prog = _make_program(["start", "out"], [_no("start"), fb, _coil("out")])
        errors = [e for e in validate_program(prog) if e.rule == "unknown_fb_type"]
        assert errors == []

    def test_unknown_fb_type_returns_error(self):
        fb = FunctionBlock.model_construct(
            block_type="WARP_DRIVE",
            instance_name="warp1",
            inputs={},
            outputs={},
        )
        rung = Rung.model_construct(elements=[fb, _coil("out")], comment="")
        prog = _make_program_bypass(["out"], [rung])
        errors = validate_program(prog)
        assert any(e.rule == "unknown_fb_type" for e in errors)

    def test_error_message_contains_instance_name_and_type(self):
        fb = FunctionBlock.model_construct(
            block_type="WARP_DRIVE",
            instance_name="warp1",
            inputs={},
            outputs={},
        )
        rung = Rung.model_construct(elements=[fb, _coil("out")], comment="")
        prog = _make_program_bypass(["out"], [rung])
        errors = [e for e in validate_program(prog) if e.rule == "unknown_fb_type"]
        assert len(errors) == 1
        assert "warp1" in errors[0].message
        assert "WARP_DRIVE" in errors[0].message

    def test_all_known_fb_types_accepted(self):
        for fb_type in FunctionBlockType:
            fb = FunctionBlock(block_type=fb_type, instance_name="inst")
            prog = _make_program(["start", "out"], [_no("start"), fb, _coil("out")])
            errors = [e for e in validate_program(prog) if e.rule == "unknown_fb_type"]
            assert errors == [], f"Unexpected error for known type {fb_type}"


# ---------------------------------------------------------------------------
# Integration: multiple rules in one program
# ---------------------------------------------------------------------------

class TestValidateIntegration:
    def test_valid_program_no_errors(self):
        prog = PLCProgram(
            title="Motor Start",
            variables=[
                _var("start_btn"),
                _var("stop_btn"),
                _var("motor_run"),
            ],
            rungs=[
                Rung(elements=[
                    _no("start_btn"),
                    _nc("stop_btn"),
                    _coil("motor_run"),
                ])
            ],
        )
        assert validate_program(prog) == []

    def test_empty_program_no_errors(self):
        assert validate_program(PLCProgram(title="Empty")) == []

    def test_rule1_and_rule2_errors_reported_together(self):
        rung = Rung.model_construct(
            elements=[_no("undeclared_x")],  # no coil AND undeclared var
            comment="",
        )
        prog = _make_program_bypass([], [rung])
        errors = validate_program(prog)
        rules = {e.rule for e in errors}
        assert "undeclared_variable" in rules
        assert "coil_count" in rules
