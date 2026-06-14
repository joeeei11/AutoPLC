"""ST 和 SCL 导出器。"""

from .models.ld import PLCProgram


def export_st(program: PLCProgram) -> str:
    """导出为 IEC 61131-3 ST 格式（.st）。"""
    lines: list[str] = []

    lines.append(f"(* {program.title} *)")
    if program.description:
        lines.append(f"(* {program.description} *)")
    lines.append("")

    lines.append("VAR")
    for var in program.variables:
        init = f" := {var.initial_value}" if var.initial_value is not None else ""
        lines.append(f"    {var.name} : {var.data_type.value}{init};")
    lines.append("END_VAR")
    lines.append("")

    lines.append(program.st_code)

    return "\n".join(lines)


def export_scl(program: PLCProgram) -> str:
    """导出为西门子 TIA Portal SCL 格式（.scl）。"""
    lines: list[str] = []

    lines.append("// TIA Portal SCL Export")
    lines.append("// Version: 1.0")
    lines.append("// Author: PLCLogicGen")
    lines.append(f"// Program: {program.title}")
    if program.description:
        lines.append(f"// Description: {program.description}")
    lines.append("")

    fb_name = _to_identifier(program.title)
    lines.append(f"FUNCTION_BLOCK \"{fb_name}\"")
    lines.append("VAR_INPUT")
    lines.append("END_VAR")
    lines.append("VAR_OUTPUT")
    lines.append("END_VAR")
    lines.append("VAR")
    for var in program.variables:
        init = f" := {var.initial_value}" if var.initial_value is not None else ""
        lines.append(f"    {var.name} : {var.data_type.value}{init};")
    lines.append("END_VAR")
    lines.append("")
    lines.append("BEGIN")
    lines.append(program.st_code)
    lines.append("END_FUNCTION_BLOCK")

    return "\n".join(lines)


def _to_identifier(title: str) -> str:
    """将标题转换为合法的 SCL 标识符（空格换下划线）。"""
    return title.replace(" ", "_")
