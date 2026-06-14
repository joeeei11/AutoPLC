"""Tests for Rockwell L5X exporter (Issue 08)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from plc_logic_gen.exporter_l5x import export_l5x
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


def _make_program() -> PLCProgram:
    return PLCProgram(
        title="Motor Control",
        description="Basic motor start/stop logic",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="stop_btn", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
            Variable(name="speed", data_type=DataType.INT, initial_value="0"),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="start_btn"),
                    Contact(type=ContactType.NC, variable="stop_btn"),
                    Coil(variable="motor_run"),
                ],
                comment="Motor start/stop logic",
            ),
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="motor_run"),
                    Coil(variable="start_btn"),
                ],
            ),
        ],
        st_code=(
            "IF start_btn AND NOT stop_btn THEN\n"
            "  motor_run := TRUE;\n"
            "END_IF"
        ),
    )


# ---------------------------------------------------------------------------
# XML 格式合法性
# ---------------------------------------------------------------------------

class TestXMLValidity:
    def test_output_is_parseable(self):
        result = export_l5x(_make_program())
        tree = ET.fromstring(result)
        assert tree is not None

    def test_returns_string(self):
        result = export_l5x(_make_program())
        assert isinstance(result, str)

    def test_xml_declaration_present(self):
        result = export_l5x(_make_program())
        assert result.startswith("<?xml")


# ---------------------------------------------------------------------------
# 根元素
# ---------------------------------------------------------------------------

class TestRootElement:
    def test_root_is_rslogix5000content(self):
        result = export_l5x(_make_program())
        root = ET.fromstring(result)
        assert root.tag == "RSLogix5000Content"

    def test_root_has_schema_revision(self):
        result = export_l5x(_make_program())
        root = ET.fromstring(result)
        assert root.get("SchemaRevision") is not None

    def test_root_has_target_name(self):
        result = export_l5x(_make_program())
        root = ET.fromstring(result)
        assert root.get("TargetName") is not None

    def test_root_has_target_type(self):
        result = export_l5x(_make_program())
        root = ET.fromstring(result)
        assert root.get("TargetType") == "Controller"


# ---------------------------------------------------------------------------
# Tag 元素（变量声明）
# ---------------------------------------------------------------------------

class TestTagElements:
    def _get_tags(self, program: PLCProgram) -> list[ET.Element]:
        result = export_l5x(program)
        root = ET.fromstring(result)
        return root.findall(".//Tag")

    def test_tag_elements_present(self):
        tags = self._get_tags(_make_program())
        assert len(tags) > 0

    def test_tag_count_matches_variables(self):
        program = _make_program()
        tags = self._get_tags(program)
        assert len(tags) == len(program.variables)

    def test_tag_names_match_variables(self):
        program = _make_program()
        tags = self._get_tags(program)
        tag_names = {t.get("Name") for t in tags}
        for var in program.variables:
            assert var.name in tag_names

    def test_tag_data_types_match(self):
        program = _make_program()
        tags = self._get_tags(program)
        tag_map = {t.get("Name"): t.get("DataType") for t in tags}
        assert tag_map["start_btn"] == "BOOL"
        assert tag_map["speed"] == "INT"

    def test_tag_initial_value_included(self):
        program = _make_program()
        tags = self._get_tags(program)
        tag_map = {t.get("Name"): t for t in tags}
        assert tag_map["speed"].get("Value") == "0"

    def test_tag_without_initial_value_has_no_value_attr(self):
        program = _make_program()
        tags = self._get_tags(program)
        tag_map = {t.get("Name"): t for t in tags}
        assert tag_map["start_btn"].get("Value") is None

    def test_no_tags_when_no_variables(self):
        program = PLCProgram(
            title="Empty",
            rungs=[Rung(elements=[Contact(type=ContactType.NO, variable="x"), Coil(variable="y")])],
        )
        tags = self._get_tags(program)
        assert len(tags) == 0


# ---------------------------------------------------------------------------
# Rung 元素
# ---------------------------------------------------------------------------

class TestRungElements:
    def _get_rungs(self, program: PLCProgram) -> list[ET.Element]:
        result = export_l5x(program)
        root = ET.fromstring(result)
        return root.findall(".//Rung")

    def test_rung_elements_present(self):
        rungs = self._get_rungs(_make_program())
        assert len(rungs) > 0

    def test_rung_count_matches_program(self):
        program = _make_program()
        rungs = self._get_rungs(program)
        assert len(rungs) == len(program.rungs)

    def test_rung_type_is_N(self):
        for rung in self._get_rungs(_make_program()):
            assert rung.get("Type") == "N"

    def test_rung_has_number_attribute(self):
        for rung in self._get_rungs(_make_program()):
            assert rung.get("Number") is not None

    def test_rung_numbers_sequential(self):
        rungs = self._get_rungs(_make_program())
        numbers = [int(r.get("Number")) for r in rungs]
        assert numbers == list(range(len(rungs)))

    def test_rung_contains_text_element(self):
        for rung in self._get_rungs(_make_program()):
            text_elem = rung.find("Text")
            assert text_elem is not None

    def test_rung_text_contains_variable_names(self):
        rungs = self._get_rungs(_make_program())
        first_text = rungs[0].find("Text").text
        assert "start_btn" in first_text
        assert "motor_run" in first_text

    def test_rung_comment_included(self):
        rungs = self._get_rungs(_make_program())
        first_comment = rungs[0].find("Comment")
        assert first_comment is not None
        assert "Motor" in first_comment.text

    def test_rung_without_comment_has_no_comment_element(self):
        rungs = self._get_rungs(_make_program())
        second_comment = rungs[1].find("Comment")
        assert second_comment is None

    def test_no_rungs_when_program_has_no_rungs(self):
        program = PLCProgram(
            title="NoRungs",
            rungs=[],
            st_code="x := TRUE;",
        )
        rungs = self._get_rungs(program)
        assert len(rungs) == 0


# ---------------------------------------------------------------------------
# ST 文本内容
# ---------------------------------------------------------------------------

class TestSTContent:
    def test_full_st_code_present(self):
        result = export_l5x(_make_program())
        assert "motor_run := TRUE" in result

    def test_nc_contact_renders_not(self):
        result = export_l5x(_make_program())
        assert "NOT stop_btn" in result

    def test_branch_in_rung(self):
        program = PLCProgram(
            title="Branch Test",
            variables=[
                Variable(name="a", data_type=DataType.BOOL),
                Variable(name="b", data_type=DataType.BOOL),
                Variable(name="out", data_type=DataType.BOOL),
            ],
            rungs=[
                Rung(elements=[
                    Branch(paths=[
                        [Contact(type=ContactType.NO, variable="a")],
                        [Contact(type=ContactType.NO, variable="b")],
                    ]),
                    Coil(variable="out"),
                ])
            ],
        )
        result = export_l5x(program)
        root = ET.fromstring(result)
        rung_text = root.find(".//Rung/Text").text
        assert "a" in rung_text
        assert "b" in rung_text
        assert "OR" in rung_text
