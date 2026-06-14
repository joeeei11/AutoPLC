"""IEC 61131-3 Ladder Diagram (LD) data model."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ContactType(str, Enum):
    NO = "NO"  # Normally Open
    NC = "NC"  # Normally Closed


class FunctionBlockType(str, Enum):
    TON = "TON"   # Timer On-Delay
    TOF = "TOF"   # Timer Off-Delay
    TP = "TP"     # Timer Pulse
    CTU = "CTU"   # Counter Up
    CTD = "CTD"   # Counter Down
    CTUD = "CTUD" # Counter Up/Down
    CMP = "CMP"   # Compare
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOVE = "MOVE"
    PID = "PID"


class DataType(str, Enum):
    BOOL = "BOOL"
    INT = "INT"
    UINT = "UINT"
    DINT = "DINT"
    REAL = "REAL"
    TIME = "TIME"
    STRING = "STRING"
    WORD = "WORD"
    DWORD = "DWORD"


class Contact(BaseModel):
    type: ContactType
    variable: str = Field(min_length=1)


class Coil(BaseModel):
    variable: str = Field(min_length=1)
    negated: bool = False


class FunctionBlock(BaseModel):
    block_type: FunctionBlockType
    instance_name: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


# Forward reference: Branch contains lists of Element, which may include Branch
Element = Annotated[Union[Contact, Coil, FunctionBlock], Field(discriminator=None)]


class Branch(BaseModel):
    """Parallel branch: a list of serial paths, each path is a list of elements."""
    paths: list[list[RungElement]] = Field(min_length=1)

    @field_validator("paths")
    @classmethod
    def paths_not_empty(cls, v: list[list[Any]]) -> list[list[Any]]:
        for i, path in enumerate(v):
            if len(path) == 0:
                raise ValueError(f"Branch path at index {i} must contain at least one element")
        return v


# RungElement can be Contact, Coil, FunctionBlock, or Branch
RungElement = Annotated[Union[Contact, Coil, FunctionBlock, Branch], Field(union_mode="left_to_right")]

# Rebuild Branch to resolve forward reference
Branch.model_rebuild()


class Rung(BaseModel):
    elements: list[RungElement] = Field(min_length=1)
    comment: str = ""

    @model_validator(mode="after")
    def validate_single_coil(self) -> "Rung":
        coil_count = _count_coils(self.elements)
        if coil_count == 0:
            raise ValueError("Rung must have at least one Coil output")
        if coil_count > 1:
            raise ValueError(f"Rung must have exactly one Coil output, found {coil_count}")
        return self


def _count_coils(elements: list[Any]) -> int:
    count = 0
    for elem in elements:
        if isinstance(elem, Coil):
            count += 1
        elif isinstance(elem, Branch):
            for path in elem.paths:
                count += _count_coils(path)
    return count


class Variable(BaseModel):
    name: str = Field(min_length=1)
    data_type: DataType
    initial_value: str | None = None


class PLCProgram(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    variables: list[Variable] = Field(default_factory=list)
    rungs: list[Rung] = Field(default_factory=list)
    st_code: str = ""
