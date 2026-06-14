"""LLM-powered PLC program generator.

Uses pydantic-ai for structured output enforcement and supports both
Anthropic Claude and OpenAI models via litellm-style model name routing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent

from plc_logic_gen.models.ld import PLCProgram
from plc_logic_gen.validator import validate_program

SYSTEM_PROMPT = """\
You are an expert PLC programmer following IEC 61131-3 standards.

When given a control logic description, produce a complete PLCProgram JSON object with:

VARIABLE RULES:
- Declare every variable referenced by Contact or Coil elements in the variables list
- Use lowercase with underscores: motor_run, temp_sensor, start_btn
- Use BOOL for digital I/O, INT/REAL for numeric signals, TIME for timer presets
- FunctionBlock input/output variables do NOT need to be in the variables list

STRUCTURE RULES:
- Each Rung must contain exactly one Coil as its output
- All Contact and Coil variables must be declared in the variables list
- FunctionBlock instances must use known types: TON, TOF, TP, CTU, CTD, CTUD, CMP, ADD, SUB, MUL, DIV, MOVE, PID
- A FunctionBlock is placed in series within a rung, always followed by a Coil

FUNCTION BLOCK RULES:
- Use TON (timer on-delay) when logic requires a time delay before an action triggers
- Use TOF (timer off-delay) when an output should stay active for a fixed time after de-energising
- Use TP (pulse timer) for a fixed-duration pulse output
- Use CTU/CTD/CTUD for counting pulses or events
- TON pin format — inputs: {"IN": "<enable_var>", "PT": "T#<duration>"}, outputs: {"Q": "<done_var>", "ET": "<elapsed_var>"}
- CTU pin format — inputs: {"CU": "<pulse_var>", "R": "<reset_var>", "PV": "<preset_int>"}, outputs: {"Q": "<reached_var>", "CV": "<count_var>"}
- Example: "restart motor 5 seconds after fault clears" → Contact(NO, "fault") then FunctionBlock(TON, "t_restart", {"IN":"fault","PT":"T#5S"}, {"Q":"restart_ready"}) then Coil("restart_coil")

BRANCH (PARALLEL / OR LOGIC) RULES:
- Use Branch when two or more contact conditions are alternatives (OR logic) for the same output
- Branch.paths is a list of serial paths; each path must have at least one element
- Place the Branch inline in rung.elements; the Coil comes AFTER the Branch — never inside a path
- Example: "activate lamp if button_a OR button_b pressed" →
    Rung(elements=[Branch(paths=[[Contact(NO,"button_a")],[Contact(NO,"button_b")]]), Coil("lamp")])
- Multiple conditions within one path are AND logic; parallel paths are OR logic

SAFETY RULES:
- Emergency stops (e_stop, estop, emergency_stop) MUST appear as NC contacts
- Never negate or bypass emergency stop inputs for safety-critical coils
- Safety interlocks must always be in series with the controlled output

OUTPUT RULES:
- Set st_code to the equivalent IEC 61131-3 Structured Text representation
- Ensure LD structure and st_code are semantically consistent

If the description lacks sufficient detail to generate valid logic (missing variables,
unclear conditions, or ambiguous actions), return a PLCProgram with an empty rungs list
and explain what information is needed in the description field.
"""


@dataclass
class GenerationError:
    """Structured error returned when generation fails or description is insufficient."""

    code: str  # "insufficient_description" | "schema_error" | "validation_failed" | "generation_failed"
    message: str
    details: list[str] = field(default_factory=list)


def _resolve_model_name(model_name: str) -> str:
    """Convert litellm-style model names to pydantic-ai provider:model format.

    Examples:
        "claude-sonnet-4-6"  -> "anthropic:claude-sonnet-4-6"
        "gpt-4o"             -> "openai:gpt-4o"
        "anthropic:..."      -> unchanged
    """
    if ":" in model_name:
        return model_name
    if "claude" in model_name.lower():
        return f"anthropic:{model_name}"
    return f"openai:{model_name}"


def generate_plc_program(
    description: str,
    brand: str = "generic",
    model_name: str = "claude-sonnet-4-6",
    *,
    _agent: Any = None,
) -> PLCProgram | GenerationError:
    """Generate a PLCProgram from a natural language description.

    Args:
        description: Natural language control logic description (Chinese or English).
        brand: Target PLC brand hint — "generic", "siemens", or "rockwell".
        model_name: LLM in litellm format — e.g. "claude-sonnet-4-6" or "gpt-4o".
        _agent: Inject a pre-built agent (or mock) for testing; skips model creation.

    Returns:
        PLCProgram on success, GenerationError on failure.
    """
    if not description or not description.strip():
        return GenerationError(
            code="insufficient_description",
            message="Description is empty. Provide a detailed control logic description.",
        )

    if _agent is None:
        resolved = _resolve_model_name(model_name)
        agent: Agent[None, PLCProgram] = Agent(
            resolved,
            output_type=PLCProgram,
            system_prompt=SYSTEM_PROMPT,
        )
    else:
        agent = _agent

    user_prompt = (
        f"Target PLC brand: {brand}\n\n"
        f"Control logic description:\n{description}"
    )

    try:
        result = agent.run_sync(user_prompt)
        program: PLCProgram = result.output
    except Exception as exc:
        return GenerationError(
            code="schema_error",
            message=f"LLM returned an invalid or unparseable response: {exc}",
        )

    # Empty rungs = LLM signalled that the description was insufficient
    if not program.rungs:
        return GenerationError(
            code="insufficient_description",
            message=(
                "Generated program has no rungs. "
                "Description may be too vague — specify variables, conditions, and actions."
            ),
            details=[program.description] if program.description else [],
        )

    errors = validate_program(program)
    if errors:
        return GenerationError(
            code="validation_failed",
            message="Generated program failed semantic validation.",
            details=[e.message for e in errors],
        )

    return program
