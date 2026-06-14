"""I/O signal extractor: uses pydantic-ai to extract IOSignal list from chat history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent

from plc_logic_gen.models.ld import IOSignal

_IO_EXTRACT_SYSTEM_PROMPT = """\
You are an expert PLC I/O signal analyst. Extract all physical I/O signals mentioned \
in the provided conversation history and return them as a structured list.

Signal type inference rules:
- Buttons, switches, proximity sensors, limit switches, relay contacts → DI (Digital Input)
- Solenoid valves, contactors, motor starters, lamps, buzzers → DO (Digital Output)
- Temperature sensors (thermocouple, RTD), pressure transmitters, flow meters, level transmitters → AI (Analog Input)
- VFD speed references, control valve positioners, analog setpoints → AO (Analog Output)

For each signal, infer a meaningful tag name using the pattern TYPE_Device_Function \
(e.g. DI_Motor_Start, AI_Temp_Inlet, DO_Valve_Open).

Return only signals that are explicitly or clearly implied in the conversation. \
Do not invent signals not mentioned.
"""


class IOSignalList(BaseModel):
    signals: list[IOSignal]


@dataclass
class IOExtractError:
    message: str


def extract_io_signals(
    messages: list[dict[str, str]],
    model_name: str = "anthropic:claude-sonnet-4-6",
    *,
    _agent: Any = None,
) -> IOSignalList | IOExtractError:
    if not messages:
        return IOExtractError(message="No messages provided")

    if _agent is None:
        agent: Agent[None, IOSignalList] = Agent(
            model_name,
            output_type=IOSignalList,
            system_prompt=_IO_EXTRACT_SYSTEM_PROMPT,
        )
    else:
        agent = _agent

    conversation_text = "\n".join(
        f"[{m['role'].upper()}]: {m['content']}" for m in messages
    )
    user_prompt = f"Extract all I/O signals from this conversation:\n\n{conversation_text}"

    try:
        result = agent.run_sync(user_prompt)
        return result.output
    except Exception as exc:
        return IOExtractError(message=f"Extraction failed: {exc}")
