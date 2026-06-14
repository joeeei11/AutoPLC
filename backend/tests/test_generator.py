"""Tests for the LLM generator (Issue 03).

All tests use mock agents — no real LLM API is ever called.

Coverage:
  - Valid description -> valid PLCProgram that passes the LD validator
  - Empty / whitespace description -> GenerationError(insufficient_description) before LLM call
  - LLM signals vague description via empty rungs -> GenerationError(insufficient_description)
  - LLM raises exception -> GenerationError(schema_error)
  - LLM returns program with undeclared variables -> GenerationError(validation_failed)
  - Model name resolver handles Claude, OpenAI, and pre-prefixed names
  - Accepted model names are passed through to agent construction
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from plc_logic_gen.generator import GenerationError, _resolve_model_name, generate_plc_program
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
from plc_logic_gen.validator import validate_program


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_program() -> PLCProgram:
    return PLCProgram(
        title="Motor Control",
        description="Basic motor start/stop",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="stop_btn", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
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
            "END_IF"
        ),
    )


def _mock_agent(program: PLCProgram) -> MagicMock:
    """Return a fake Agent whose run_sync() yields the given program."""
    result = MagicMock()
    result.output = program
    agent = MagicMock()
    agent.run_sync.return_value = result
    return agent


# ---------------------------------------------------------------------------
# Valid generation
# ---------------------------------------------------------------------------

class TestValidGeneration:
    def test_returns_plc_program_instance(self):
        program = _make_valid_program()
        result = generate_plc_program(
            "Start motor with start button, stop with stop button",
            _agent=_mock_agent(program),
        )
        assert isinstance(result, PLCProgram)

    def test_program_title_preserved(self):
        program = _make_valid_program()
        result = generate_plc_program("Motor start/stop", _agent=_mock_agent(program))
        assert isinstance(result, PLCProgram)
        assert result.title == "Motor Control"

    def test_program_passes_ld_validator(self):
        """Acceptance criterion: returned PLCProgram passes Issue-02 validator."""
        program = _make_valid_program()
        result = generate_plc_program(
            "Control motor with start and stop buttons",
            _agent=_mock_agent(program),
        )
        assert isinstance(result, PLCProgram)
        assert validate_program(result) == []

    def test_brand_parameter_forwarded(self):
        program = _make_valid_program()
        agent = _mock_agent(program)
        generate_plc_program("Motor control", brand="siemens", _agent=agent)
        call_args = agent.run_sync.call_args[0][0]
        assert "siemens" in call_args.lower()

    def test_description_forwarded_to_agent(self):
        program = _make_valid_program()
        agent = _mock_agent(program)
        generate_plc_program("Start motor when button pressed", _agent=agent)
        call_args = agent.run_sync.call_args[0][0]
        assert "Start motor when button pressed" in call_args


# ---------------------------------------------------------------------------
# Insufficient description — pre-check (before LLM call)
# ---------------------------------------------------------------------------

class TestInsufficientDescriptionPreCheck:
    def test_empty_string_returns_error(self):
        result = generate_plc_program("")
        assert isinstance(result, GenerationError)
        assert result.code == "insufficient_description"

    def test_whitespace_only_returns_error(self):
        result = generate_plc_program("   \t\n  ")
        assert isinstance(result, GenerationError)
        assert result.code == "insufficient_description"

    def test_empty_description_no_agent_call(self):
        agent = MagicMock()
        generate_plc_program("", _agent=agent)
        agent.run_sync.assert_not_called()


# ---------------------------------------------------------------------------
# Insufficient description — LLM signals via empty rungs
# ---------------------------------------------------------------------------

class TestInsufficientDescriptionViaEmptyRungs:
    def test_empty_rungs_returns_error(self):
        vague_program = PLCProgram(
            title="Unclear",
            description="Need more details: specify inputs, outputs, conditions.",
        )
        result = generate_plc_program("something", _agent=_mock_agent(vague_program))
        assert isinstance(result, GenerationError)
        assert result.code == "insufficient_description"

    def test_error_message_mentions_vagueness(self):
        vague_program = PLCProgram(title="Unclear")
        result = generate_plc_program("vague", _agent=_mock_agent(vague_program))
        assert isinstance(result, GenerationError)
        assert "vague" in result.message.lower() or "rung" in result.message.lower()

    def test_program_description_included_in_details(self):
        vague_program = PLCProgram(
            title="Unclear",
            description="Please specify the sensor variable name.",
        )
        result = generate_plc_program("unclear", _agent=_mock_agent(vague_program))
        assert isinstance(result, GenerationError)
        assert any("specify" in d.lower() for d in result.details)


# ---------------------------------------------------------------------------
# LLM schema / unexpected error path
# ---------------------------------------------------------------------------

class TestSchemaErrorPath:
    def test_agent_exception_returns_schema_error(self):
        agent = MagicMock()
        agent.run_sync.side_effect = ValueError("LLM returned malformed JSON")
        result = generate_plc_program("Motor control logic", _agent=agent)
        assert isinstance(result, GenerationError)
        assert result.code == "schema_error"

    def test_schema_error_message_contains_exception_text(self):
        agent = MagicMock()
        agent.run_sync.side_effect = RuntimeError("Unexpected token at position 42")
        result = generate_plc_program("Conveyor belt counter", _agent=agent)
        assert isinstance(result, GenerationError)
        assert "Unexpected token at position 42" in result.message

    def test_retry_failure_returns_schema_error(self):
        """Simulate pydantic-ai exhausting retries and raising."""
        agent = MagicMock()
        agent.run_sync.side_effect = Exception("Max retries exceeded: schema mismatch")
        result = generate_plc_program("PID temperature control", _agent=agent)
        assert isinstance(result, GenerationError)
        assert result.code == "schema_error"


# ---------------------------------------------------------------------------
# Validation failure path
# ---------------------------------------------------------------------------

class TestValidationFailurePath:
    def test_undeclared_variable_returns_validation_error(self):
        """LLM returns a structurally valid program that fails semantic validation."""
        bad_program = PLCProgram.model_construct(
            title="Bad",
            description="",
            variables=[],
            rungs=[
                Rung.model_construct(
                    elements=[
                        Contact(type=ContactType.NO, variable="ghost_sensor"),
                        Coil(variable="ghost_output"),
                    ],
                    comment="",
                )
            ],
            st_code="",
        )
        result = generate_plc_program("Some logic", _agent=_mock_agent(bad_program))
        assert isinstance(result, GenerationError)
        assert result.code == "validation_failed"

    def test_validation_error_details_populated(self):
        bad_program = PLCProgram.model_construct(
            title="Bad",
            description="",
            variables=[],
            rungs=[
                Rung.model_construct(
                    elements=[
                        Contact(type=ContactType.NO, variable="undeclared_x"),
                        Coil(variable="undeclared_y"),
                    ],
                    comment="",
                )
            ],
            st_code="",
        )
        result = generate_plc_program("Logic", _agent=_mock_agent(bad_program))
        assert isinstance(result, GenerationError)
        assert len(result.details) >= 1
        assert any("undeclared" in d.lower() for d in result.details)


# ---------------------------------------------------------------------------
# Model name resolution
# ---------------------------------------------------------------------------

class TestModelNameResolution:
    def test_claude_name_gets_anthropic_prefix(self):
        assert _resolve_model_name("claude-sonnet-4-6") == "anthropic:claude-sonnet-4-6"

    def test_claude_3_name_gets_anthropic_prefix(self):
        assert _resolve_model_name("claude-3-5-sonnet-20241022") == "anthropic:claude-3-5-sonnet-20241022"

    def test_gpt_name_gets_openai_prefix(self):
        assert _resolve_model_name("gpt-4o") == "openai:gpt-4o"

    def test_gpt_4_turbo_gets_openai_prefix(self):
        assert _resolve_model_name("gpt-4-turbo") == "openai:gpt-4-turbo"

    def test_already_prefixed_anthropic_unchanged(self):
        assert _resolve_model_name("anthropic:claude-sonnet-4-6") == "anthropic:claude-sonnet-4-6"

    def test_already_prefixed_openai_unchanged(self):
        assert _resolve_model_name("openai:gpt-4o") == "openai:gpt-4o"

    def test_unknown_model_defaults_to_openai_prefix(self):
        assert _resolve_model_name("some-custom-model") == "openai:some-custom-model"


# ---------------------------------------------------------------------------
# Environment variable reading (structural check only, no real calls)
# ---------------------------------------------------------------------------

class TestEnvVarSupport:
    def test_generate_accepts_claude_model_name(self):
        """Smoke test: generate_plc_program accepts the default Claude model name."""
        program = _make_valid_program()
        result = generate_plc_program(
            "Motor start/stop",
            model_name="claude-sonnet-4-6",
            _agent=_mock_agent(program),
        )
        assert isinstance(result, PLCProgram)

    def test_generate_accepts_openai_model_name(self):
        """Smoke test: generate_plc_program accepts an OpenAI model name."""
        program = _make_valid_program()
        result = generate_plc_program(
            "Motor start/stop",
            model_name="gpt-4o",
            _agent=_mock_agent(program),
        )
        assert isinstance(result, PLCProgram)


# ---------------------------------------------------------------------------
# FunctionBlock generation (Issue 13)
# ---------------------------------------------------------------------------

def _make_ton_restart_program() -> PLCProgram:
    """Motor stops on high temp; TON timer delays 5 s before restart signal."""
    return PLCProgram(
        title="Temperature Motor Control",
        description="Motor stops on over-temperature, restarts after 5-second delay",
        variables=[
            Variable(name="over_temp", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
            Variable(name="timer_active", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NC, variable="over_temp"),
                    Coil(variable="motor_run"),
                ],
                comment="Motor runs while temperature is normal",
            ),
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="over_temp"),
                    FunctionBlock(
                        block_type=FunctionBlockType.TON,
                        instance_name="t_restart",
                        inputs={"IN": "over_temp", "PT": "T#5S"},
                        outputs={"Q": "restart_ready", "ET": "elapsed"},
                    ),
                    Coil(variable="timer_active"),
                ],
                comment="5-second restart delay timer",
            ),
        ],
        st_code=(
            "IF NOT over_temp THEN motor_run := TRUE; ELSE motor_run := FALSE; END_IF\n"
            "t_restart(IN := over_temp, PT := T#5S);\n"
            "timer_active := t_restart.Q;"
        ),
    )


class TestFunctionBlockGeneration:
    """Mock tests for FunctionBlock (TON timer) generation scenario."""

    def test_ton_program_returned_as_plc_program(self):
        result = generate_plc_program(
            "电机在温度超过 80°C 时停止，延时 5 秒后重启",
            _agent=_mock_agent(_make_ton_restart_program()),
        )
        assert isinstance(result, PLCProgram)

    def test_ton_program_contains_function_block(self):
        result = generate_plc_program(
            "电机在温度超过 80°C 时停止，延时 5 秒后重启",
            _agent=_mock_agent(_make_ton_restart_program()),
        )
        assert isinstance(result, PLCProgram)
        fb_elements = [
            elem
            for rung in result.rungs
            for elem in rung.elements
            if isinstance(elem, FunctionBlock)
        ]
        assert len(fb_elements) >= 1

    def test_ton_program_uses_ton_block_type(self):
        result = generate_plc_program(
            "电机在温度超过 80°C 时停止，延时 5 秒后重启",
            _agent=_mock_agent(_make_ton_restart_program()),
        )
        assert isinstance(result, PLCProgram)
        ton_blocks = [
            elem
            for rung in result.rungs
            for elem in rung.elements
            if isinstance(elem, FunctionBlock) and elem.block_type == FunctionBlockType.TON
        ]
        assert len(ton_blocks) >= 1

    def test_ton_program_passes_validator(self):
        result = generate_plc_program(
            "电机在温度超过 80°C 时停止，延时 5 秒后重启",
            _agent=_mock_agent(_make_ton_restart_program()),
        )
        assert isinstance(result, PLCProgram)
        assert validate_program(result) == []

    def test_ton_timer_preset_in_inputs(self):
        result = generate_plc_program(
            "电机在温度超过 80°C 时停止，延时 5 秒后重启",
            _agent=_mock_agent(_make_ton_restart_program()),
        )
        assert isinstance(result, PLCProgram)
        ton_block = next(
            elem
            for rung in result.rungs
            for elem in rung.elements
            if isinstance(elem, FunctionBlock) and elem.block_type == FunctionBlockType.TON
        )
        assert "PT" in ton_block.inputs
        assert "IN" in ton_block.inputs


# ---------------------------------------------------------------------------
# Branch (OR logic) generation (Issue 13)
# ---------------------------------------------------------------------------

def _make_or_branch_program() -> PLCProgram:
    """Lamp activates when button_a OR button_b is pressed."""
    return PLCProgram(
        title="OR Button Lamp",
        description="Activate lamp when either button A or button B is pressed",
        variables=[
            Variable(name="button_a", data_type=DataType.BOOL),
            Variable(name="button_b", data_type=DataType.BOOL),
            Variable(name="lamp", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Branch(paths=[
                        [Contact(type=ContactType.NO, variable="button_a")],
                        [Contact(type=ContactType.NO, variable="button_b")],
                    ]),
                    Coil(variable="lamp"),
                ],
                comment="Lamp on if button_a OR button_b pressed",
            )
        ],
        st_code="lamp := button_a OR button_b;",
    )


class TestBranchGeneration:
    """Mock tests for Branch (parallel/OR logic) generation scenario."""

    def test_branch_program_returned_as_plc_program(self):
        result = generate_plc_program(
            "按下按钮A或按钮B时，启动指示灯",
            _agent=_mock_agent(_make_or_branch_program()),
        )
        assert isinstance(result, PLCProgram)

    def test_branch_program_contains_branch(self):
        result = generate_plc_program(
            "按下按钮A或按钮B时，启动指示灯",
            _agent=_mock_agent(_make_or_branch_program()),
        )
        assert isinstance(result, PLCProgram)
        branches = [
            elem
            for rung in result.rungs
            for elem in rung.elements
            if isinstance(elem, Branch)
        ]
        assert len(branches) >= 1

    def test_branch_has_two_parallel_paths(self):
        result = generate_plc_program(
            "按下按钮A或按钮B时，启动指示灯",
            _agent=_mock_agent(_make_or_branch_program()),
        )
        assert isinstance(result, PLCProgram)
        branch = next(
            elem
            for rung in result.rungs
            for elem in rung.elements
            if isinstance(elem, Branch)
        )
        assert len(branch.paths) == 2

    def test_branch_program_passes_validator(self):
        result = generate_plc_program(
            "按下按钮A或按钮B时，启动指示灯",
            _agent=_mock_agent(_make_or_branch_program()),
        )
        assert isinstance(result, PLCProgram)
        assert validate_program(result) == []

    def test_branch_coil_not_inside_path(self):
        """Coil must be outside the branch paths (comes after the Branch in the rung)."""
        result = generate_plc_program(
            "按下按钮A或按钮B时，启动指示灯",
            _agent=_mock_agent(_make_or_branch_program()),
        )
        assert isinstance(result, PLCProgram)
        for rung in result.rungs:
            for elem in rung.elements:
                if isinstance(elem, Branch):
                    for path in elem.paths:
                        for path_elem in path:
                            assert not isinstance(path_elem, Coil), (
                                "Coil must not appear inside a Branch path"
                            )
