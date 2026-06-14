"""罗克韦尔 L5X 导出器。"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

from .models.ld import PLCProgram


_L5X_VERSION = "1.0"
_SCHEMA_REVISION = "1"


def export_l5x(program: PLCProgram) -> str:
    """导出为罗克韦尔 Studio 5000 L5X 格式（.L5X）。"""
    root = ET.Element("RSLogix5000Content")
    root.set("SchemaRevision", _SCHEMA_REVISION)
    root.set("SoftwareRevision", "35.00")
    root.set("TargetName", _to_identifier(program.title))
    root.set("TargetType", "Controller")
    root.set("ExportOptions", "References NoRawData L5KData DecoratedData Context Dependencies ForceProtectedEncoding AllProjDocTrans")

    controller = ET.SubElement(root, "Controller")
    controller.set("Name", _to_identifier(program.title))
    controller.set("ProcessorType", "1769-L33ERM")
    controller.set("MajorRev", "35")
    controller.set("MinorRev", "0")
    if program.description:
        desc_elem = ET.SubElement(controller, "Description")
        desc_elem.text = program.description

    tags_elem = ET.SubElement(controller, "Tags")
    for var in program.variables:
        tag = ET.SubElement(tags_elem, "Tag")
        tag.set("Name", var.name)
        tag.set("TagType", "Base")
        tag.set("DataType", var.data_type.value)
        tag.set("Usage", "Public")
        if var.initial_value is not None:
            tag.set("Value", var.initial_value)

    programs_elem = ET.SubElement(controller, "Programs")
    prog_elem = ET.SubElement(programs_elem, "Program")
    prog_elem.set("Name", _to_identifier(program.title))

    routines_elem = ET.SubElement(prog_elem, "Routines")
    routine = ET.SubElement(routines_elem, "Routine")
    routine.set("Name", "MainRoutine")
    routine.set("Type", "ST")

    st_content = ET.SubElement(routine, "STContent")

    for i, rung in enumerate(program.rungs):
        rung_elem = ET.SubElement(st_content, "Rung")
        rung_elem.set("Number", str(i))
        rung_elem.set("Type", "N")
        if rung.comment:
            comment_elem = ET.SubElement(rung_elem, "Comment")
            comment_elem.text = rung.comment
        text_elem = ET.SubElement(rung_elem, "Text")
        text_elem.text = _rung_to_st(rung)

    if program.st_code:
        full_st = ET.SubElement(routine, "FullST")
        full_st.text = program.st_code

    return _pretty_print(root)


def _rung_to_st(rung) -> str:
    """将 Rung 元素列表序列化为简单 ST 文本。"""
    from .models.ld import Contact, ContactType, Coil, FunctionBlock, Branch

    parts: list[str] = []

    def _process(elements) -> list[str]:
        tokens: list[str] = []
        for elem in elements:
            if isinstance(elem, Contact):
                if elem.type == ContactType.NC:
                    tokens.append(f"NOT {elem.variable}")
                else:
                    tokens.append(elem.variable)
            elif isinstance(elem, Coil):
                tokens.append(f"[{elem.variable}]")
            elif isinstance(elem, Branch):
                branch_parts = [" AND ".join(_process(path)) for path in elem.paths]
                tokens.append("(" + " OR ".join(branch_parts) + ")")
            elif isinstance(elem, FunctionBlock):
                tokens.append(f"{elem.instance_name}({elem.block_type.value})")
        return tokens

    tokens = _process(rung.elements)
    return " AND ".join(tokens)


def _to_identifier(title: str) -> str:
    return title.replace(" ", "_")


def _pretty_print(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="unicode", xml_declaration=False)
    reparsed = minidom.parseString(raw)
    pretty = reparsed.toprettyxml(indent="  ", encoding=None)
    # toprettyxml 会加 <?xml ...?> 声明，替换为标准声明
    lines = pretty.splitlines()
    # 替换首行为标准 XML 声明
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return "\n".join(lines)
