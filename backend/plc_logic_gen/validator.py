"""Pure-function validator for PLCProgram objects.

Returns a list of LDError; an empty list means the program is valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from plc_logic_gen.models.ld import Branch, Coil, Contact, FunctionBlock, FunctionBlockType, PLCProgram


@dataclass
class LDError:
    rule: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


def validate_program(program: PLCProgram) -> list[LDError]:
    declared = {v.name for v in program.variables}
    errors: list[LDError] = []
    for idx, rung in enumerate(program.rungs):
        errors.extend(_check_undeclared_variables(rung.elements, declared, idx))
        errors.extend(_check_coil_count(rung.elements, idx))
        errors.extend(_check_empty_branch_paths(rung.elements, idx))
        errors.extend(_check_fb_types(rung.elements, idx))
    return errors


# --- Rule 1: all Contact/Coil variables must be declared ---

def _check_undeclared_variables(
    elements: list[Any], declared: set[str], rung_idx: int
) -> list[LDError]:
    errors: list[LDError] = []
    for elem in elements:
        if isinstance(elem, (Contact, Coil)):
            if elem.variable not in declared:
                kind = "Contact" if isinstance(elem, Contact) else "Coil"
                errors.append(LDError(
                    rule="undeclared_variable",
                    message=(
                        f"Rung {rung_idx}: {kind} references undeclared variable '{elem.variable}'"
                    ),
                    context={"variable": elem.variable, "rung": rung_idx},
                ))
        elif isinstance(elem, Branch):
            for path in elem.paths:
                errors.extend(_check_undeclared_variables(path, declared, rung_idx))
    return errors


# --- Rule 2: each Rung must have exactly one Coil output ---

def _count_coils(elements: list[Any]) -> int:
    count = 0
    for elem in elements:
        if isinstance(elem, Coil):
            count += 1
        elif isinstance(elem, Branch):
            for path in elem.paths:
                count += _count_coils(path)
    return count


def _check_coil_count(elements: list[Any], rung_idx: int) -> list[LDError]:
    count = _count_coils(elements)
    if count == 0:
        return [LDError(
            rule="coil_count",
            message=f"Rung {rung_idx}: must have at least one Coil output, found 0",
            context={"rung": rung_idx, "coil_count": 0},
        )]
    if count > 1:
        return [LDError(
            rule="coil_count",
            message=f"Rung {rung_idx}: must have exactly one Coil output, found {count}",
            context={"rung": rung_idx, "coil_count": count},
        )]
    return []


# --- Rule 3: every Branch path must have at least one element ---

def _check_empty_branch_paths(elements: list[Any], rung_idx: int) -> list[LDError]:
    errors: list[LDError] = []
    for elem in elements:
        if isinstance(elem, Branch):
            for path_idx, path in enumerate(elem.paths):
                if len(path) == 0:
                    errors.append(LDError(
                        rule="empty_branch_path",
                        message=(
                            f"Rung {rung_idx}: Branch path at index {path_idx} is empty"
                        ),
                        context={"rung": rung_idx, "path_index": path_idx},
                    ))
                else:
                    errors.extend(_check_empty_branch_paths(path, rung_idx))
    return errors


# --- Rule 4: FunctionBlock.block_type must be a known FunctionBlockType ---

def _check_fb_types(elements: list[Any], rung_idx: int) -> list[LDError]:
    errors: list[LDError] = []
    for elem in elements:
        if isinstance(elem, FunctionBlock):
            if not isinstance(elem.block_type, FunctionBlockType):
                errors.append(LDError(
                    rule="unknown_fb_type",
                    message=(
                        f"Rung {rung_idx}: FunctionBlock '{elem.instance_name}' "
                        f"has unknown type '{elem.block_type}'"
                    ),
                    context={
                        "rung": rung_idx,
                        "instance_name": elem.instance_name,
                        "block_type": str(elem.block_type),
                    },
                ))
        elif isinstance(elem, Branch):
            for path in elem.paths:
                errors.extend(_check_fb_types(path, rung_idx))
    return errors
