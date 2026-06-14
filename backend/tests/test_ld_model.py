"""Unit tests for LD data model."""

import pytest
from pydantic import ValidationError

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


# --- ContactType ---

class TestContactType:
    def test_no_and_nc_values(self):
        assert ContactType.NO == "NO"
        assert ContactType.NC == "NC"

    def test_invalid_contact_type_raises(self):
        with pytest.raises(ValidationError):
            Contact(type="XX", variable="x")


# --- Contact ---

class TestContact:
    def test_valid_no_contact(self):
        c = Contact(type=ContactType.NO, variable="start_btn")
        assert c.type == ContactType.NO
        assert c.variable == "start_btn"

    def test_valid_nc_contact(self):
        c = Contact(type=ContactType.NC, variable="e_stop")
        assert c.type == ContactType.NC

    def test_empty_variable_raises(self):
        with pytest.raises(ValidationError):
            Contact(type=ContactType.NO, variable="")


# --- Coil ---

class TestCoil:
    def test_default_not_negated(self):
        coil = Coil(variable="motor_run")
        assert coil.negated is False

    def test_negated_coil(self):
        coil = Coil(variable="alarm", negated=True)
        assert coil.negated is True

    def test_empty_variable_raises(self):
        with pytest.raises(ValidationError):
            Coil(variable="")


# --- FunctionBlock ---

class TestFunctionBlock:
    def test_valid_ton_block(self):
        fb = FunctionBlock(
            block_type=FunctionBlockType.TON,
            instance_name="timer1",
            inputs={"IN": "start_btn", "PT": "T#5s"},
            outputs={"Q": "motor_run"},
        )
        assert fb.block_type == FunctionBlockType.TON
        assert fb.instance_name == "timer1"

    def test_default_empty_inputs_outputs(self):
        fb = FunctionBlock(block_type=FunctionBlockType.CTU, instance_name="cnt1")
        assert fb.inputs == {}
        assert fb.outputs == {}

    def test_invalid_block_type_raises(self):
        with pytest.raises(ValidationError):
            FunctionBlock(block_type="UNKNOWN", instance_name="x")

    def test_empty_instance_name_raises(self):
        with pytest.raises(ValidationError):
            FunctionBlock(block_type=FunctionBlockType.TON, instance_name="")


# --- Branch ---

class TestBranch:
    def test_valid_two_path_branch(self):
        branch = Branch(paths=[
            [Contact(type=ContactType.NO, variable="a")],
            [Contact(type=ContactType.NC, variable="b")],
        ])
        assert len(branch.paths) == 2

    def test_empty_path_list_raises(self):
        with pytest.raises(ValidationError):
            Branch(paths=[])

    def test_empty_inner_path_raises(self):
        with pytest.raises(ValidationError):
            Branch(paths=[[]])

    def test_nested_branch(self):
        inner = Branch(paths=[
            [Contact(type=ContactType.NO, variable="x")],
            [Contact(type=ContactType.NC, variable="y")],
        ])
        outer = Branch(paths=[
            [inner, Coil(variable="out")],
        ])
        assert len(outer.paths[0]) == 2


# --- Rung ---

class TestRung:
    def _simple_rung(self):
        return Rung(elements=[
            Contact(type=ContactType.NO, variable="start"),
            Coil(variable="motor"),
        ])

    def test_valid_rung(self):
        rung = self._simple_rung()
        assert len(rung.elements) == 2

    def test_default_empty_comment(self):
        rung = self._simple_rung()
        assert rung.comment == ""

    def test_missing_coil_raises(self):
        with pytest.raises(ValidationError, match="at least one Coil"):
            Rung(elements=[Contact(type=ContactType.NO, variable="x")])

    def test_multiple_coils_raises(self):
        with pytest.raises(ValidationError, match="exactly one Coil"):
            Rung(elements=[
                Coil(variable="a"),
                Coil(variable="b"),
            ])

    def test_empty_elements_raises(self):
        with pytest.raises(ValidationError):
            Rung(elements=[])

    def test_rung_with_function_block(self):
        fb = FunctionBlock(block_type=FunctionBlockType.TON, instance_name="t1")
        rung = Rung(elements=[
            Contact(type=ContactType.NO, variable="start"),
            fb,
            Coil(variable="motor"),
        ])
        assert len(rung.elements) == 3

    def test_rung_with_branch(self):
        branch = Branch(paths=[
            [Contact(type=ContactType.NO, variable="a")],
            [Contact(type=ContactType.NC, variable="b")],
        ])
        rung = Rung(elements=[branch, Coil(variable="out")])
        assert len(rung.elements) == 2


# --- Variable ---

class TestVariable:
    def test_valid_bool_variable(self):
        v = Variable(name="motor_run", data_type=DataType.BOOL)
        assert v.data_type == DataType.BOOL
        assert v.initial_value is None

    def test_with_initial_value(self):
        v = Variable(name="speed", data_type=DataType.INT, initial_value="0")
        assert v.initial_value == "0"

    def test_invalid_data_type_raises(self):
        with pytest.raises(ValidationError):
            Variable(name="x", data_type="FLOAT")

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            Variable(name="", data_type=DataType.BOOL)


# --- PLCProgram ---

class TestPLCProgram:
    def _make_program(self):
        return PLCProgram(
            title="Motor Control",
            description="Simple motor start/stop",
            variables=[
                Variable(name="start_btn", data_type=DataType.BOOL),
                Variable(name="stop_btn", data_type=DataType.BOOL),
                Variable(name="motor_run", data_type=DataType.BOOL),
            ],
            rungs=[
                Rung(elements=[
                    Contact(type=ContactType.NO, variable="start_btn"),
                    Contact(type=ContactType.NC, variable="stop_btn"),
                    Coil(variable="motor_run"),
                ])
            ],
            st_code="IF start_btn AND NOT stop_btn THEN motor_run := TRUE; END_IF",
        )

    def test_valid_program(self):
        prog = self._make_program()
        assert prog.title == "Motor Control"
        assert len(prog.rungs) == 1
        assert len(prog.variables) == 3

    def test_default_empty_rungs_and_variables(self):
        prog = PLCProgram(title="Empty")
        assert prog.rungs == []
        assert prog.variables == []
        assert prog.st_code == ""

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            PLCProgram(title="")

    def test_multiple_rungs(self):
        prog = PLCProgram(
            title="Multi-rung",
            rungs=[
                Rung(elements=[
                    Contact(type=ContactType.NO, variable="a"),
                    Coil(variable="out1"),
                ]),
                Rung(elements=[
                    Contact(type=ContactType.NC, variable="b"),
                    Coil(variable="out2"),
                ]),
            ],
        )
        assert len(prog.rungs) == 2

    def test_program_json_roundtrip(self):
        prog = self._make_program()
        json_str = prog.model_dump_json()
        restored = PLCProgram.model_validate_json(json_str)
        assert restored.title == prog.title
        assert len(restored.rungs) == len(prog.rungs)
        assert len(restored.variables) == len(prog.variables)


# --- Import completeness ---

class TestImports:
    def test_all_types_importable_from_models(self):
        from plc_logic_gen.models import (  # noqa: F401
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
