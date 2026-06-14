"""Pure-function validator for PLCProgram objects.

Pydantic model validators in models/ld.py already enforce structural rules
(coil count, branch path non-empty, known FunctionBlock types).  This module
handles only cross-entity semantic rules that Pydantic cannot express.

Returns a list of LDError; an empty list means the program is valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from plc_logic_gen.models.ld import Branch, Coil, Contact, FunctionBlock, FunctionBlockType, PLCProgram

_NAMING_RE = re.compile(r"^[A-Z]{1,4}_[A-Za-z0-9]+_[A-Za-z0-9]+$")


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
    errors.extend(_check_naming_convention(program))
    return errors


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


def _check_coil_count(elements: list[Any], rung_idx: int) -> list[LDError]:
    count = _count_coils(elements)
    if count != 1:
        return [LDError(
            rule="coil_count",
            message=f"Rung {rung_idx}: expected exactly 1 Coil, found {count}",
            context={"rung": rung_idx, "count": count},
        )]
    return []


def _count_coils(elements: list[Any]) -> int:
    count = 0
    for elem in elements:
        if isinstance(elem, Coil):
            count += 1
        elif isinstance(elem, Branch):
            for path in elem.paths:
                count += _count_coils(path)
    return count


def _check_empty_branch_paths(elements: list[Any], rung_idx: int) -> list[LDError]:
    errors: list[LDError] = []
    for elem in elements:
        if isinstance(elem, Branch):
            for i, path in enumerate(elem.paths):
                if len(path) == 0:
                    errors.append(LDError(
                        rule="empty_branch_path",
                        message=f"Rung {rung_idx}: Branch path at index {i} is empty",
                        context={"rung": rung_idx, "path_index": i},
                    ))
    return errors


def _check_fb_types(elements: list[Any], rung_idx: int) -> list[LDError]:
    errors: list[LDError] = []
    known = {t.value for t in FunctionBlockType}
    for elem in elements:
        if isinstance(elem, FunctionBlock):
            bt = elem.block_type.value if isinstance(elem.block_type, FunctionBlockType) else str(elem.block_type)
            if bt not in known:
                errors.append(LDError(
                    rule="unknown_fb_type",
                    message=f"Rung {rung_idx}: FunctionBlock '{elem.instance_name}' has unknown type '{bt}'",
                    context={"rung": rung_idx, "instance": elem.instance_name, "type": bt},
                ))
        elif isinstance(elem, Branch):
            for path in elem.paths:
                errors.extend(_check_fb_types(path, rung_idx))
    return errors


def _check_naming_convention(program: PLCProgram) -> list[LDError]:
    errors: list[LDError] = []
    for var in program.variables:
        if not _NAMING_RE.match(var.name):
            errors.append(LDError(
                rule="naming_convention",
                message=(
                    f"Variable '{var.name}' does not follow naming convention "
                    "[TypePrefix]_[Object]_[Action] (e.g. DI_Motor_Start)"
                ),
                context={"variable": var.name},
            ))
    return errors
