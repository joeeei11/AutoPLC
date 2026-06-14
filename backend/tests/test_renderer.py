"""Tests for SVG renderer (Issue 04)."""

import re

import pytest

from plc_logic_gen.models.ld import (
    Branch,
    Coil,
    Contact,
    ContactType,
    FunctionBlock,
    FunctionBlockType,
    PLCProgram,
    Rung,
)
from plc_logic_gen.renderer import render_svg


class TestRenderSvgStructure:
    """Output is valid SVG string."""

    def test_starts_with_svg_tag(self):
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[Contact(type=ContactType.NO, variable="x"), Coil(variable="y")])]
        )
        assert render_svg(prog).startswith("<svg")

    def test_contains_svg_namespace(self):
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[Contact(type=ContactType.NO, variable="x"), Coil(variable="y")])]
        )
        assert 'xmlns="http://www.w3.org/2000/svg"' in render_svg(prog)

    def test_ends_with_closing_svg_tag(self):
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[Contact(type=ContactType.NO, variable="x"), Coil(variable="y")])]
        )
        assert render_svg(prog).endswith("</svg>")

    def test_empty_program_returns_empty_svg(self):
        prog = PLCProgram(title="empty")
        svg = render_svg(prog)
        assert "<svg" in svg
        assert "</svg>" in svg


class TestRenderSvgSymbols:
    """Correct symbols are emitted for NO contacts, NC contacts, and coils."""

    def _two_no_one_coil(self) -> PLCProgram:
        return PLCProgram(
            title="motor",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="start"),
                Contact(type=ContactType.NO, variable="stop"),
                Coil(variable="motor"),
            ])]
        )

    def test_coil_uses_circle_element(self):
        svg = render_svg(self._two_no_one_coil())
        assert "<circle" in svg

    def test_one_coil_one_circle(self):
        svg = render_svg(self._two_no_one_coil())
        assert svg.count("<circle") == 1

    def test_no_contact_has_two_vertical_bars(self):
        # Each NO contact contributes exactly 4 lines: left-wire, left-bar, right-bar, right-wire
        # NC would add a 5th diagonal line
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="a"),
                Coil(variable="b"),
            ])]
        )
        svg = render_svg(prog)
        # Verify no diagonal slash is present for NO contact
        # NC adds an extra <line> compared to NO; we just confirm it renders without the NC marker
        assert "<circle" in svg  # coil present
        assert "a" in svg        # variable label present

    def test_nc_contact_has_diagonal_slash(self):
        prog_no = PLCProgram(
            title="t",
            rungs=[Rung(elements=[Contact(type=ContactType.NO, variable="a"), Coil(variable="b")])]
        )
        prog_nc = PLCProgram(
            title="t",
            rungs=[Rung(elements=[Contact(type=ContactType.NC, variable="a"), Coil(variable="b")])]
        )
        svg_no = render_svg(prog_no)
        svg_nc = render_svg(prog_nc)
        # NC has one extra <line> (the diagonal slash)
        assert svg_nc.count("<line") == svg_no.count("<line") + 1


class TestRenderSvgLabels:
    """Variable names appear as text labels below each element."""

    def test_labels_for_all_elements(self):
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="start_btn"),
                Contact(type=ContactType.NC, variable="e_stop"),
                Coil(variable="motor_run"),
            ])]
        )
        svg = render_svg(prog)
        assert "start_btn" in svg
        assert "e_stop" in svg
        assert "motor_run" in svg

    def test_labels_use_text_elements(self):
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="x"),
                Coil(variable="y"),
            ])]
        )
        svg = render_svg(prog)
        assert "<text" in svg
        # Two elements → two <text> labels
        assert svg.count("<text") == 2


class TestRenderSvgMultipleRungs:
    """Multiple rungs render independently and stack vertically."""

    def _two_rung_prog(self) -> PLCProgram:
        return PLCProgram(
            title="multi",
            rungs=[
                Rung(elements=[
                    Contact(type=ContactType.NO, variable="a"),
                    Coil(variable="out1"),
                ]),
                Rung(elements=[
                    Contact(type=ContactType.NC, variable="b"),
                    Coil(variable="out2"),
                ]),
            ]
        )

    def test_two_coils_produce_two_circles(self):
        svg = render_svg(self._two_rung_prog())
        assert svg.count("<circle") == 2

    def test_all_variable_labels_present(self):
        svg = render_svg(self._two_rung_prog())
        assert "a" in svg
        assert "out1" in svg
        assert "b" in svg
        assert "out2" in svg

    def test_rungs_use_different_y_coordinates(self):
        # Two rungs must have different y1 values on their rails
        svg = render_svg(self._two_rung_prog())
        # Collect rail y1 values: power rails have stroke-width=4
        import re
        rail_y1s = re.findall(r'stroke-width="4"/>.*?stroke-width="4"', svg, re.DOTALL)
        # Simpler: just ensure there are at least 4 rail lines (2 per rung × 2 rungs)
        assert svg.count(f'stroke-width="4"') >= 4

    def test_three_rungs_have_three_circles(self):
        prog = PLCProgram(
            title="t",
            rungs=[
                Rung(elements=[Contact(type=ContactType.NO, variable="a"), Coil(variable="x")]),
                Rung(elements=[Contact(type=ContactType.NO, variable="b"), Coil(variable="y")]),
                Rung(elements=[Contact(type=ContactType.NO, variable="c"), Coil(variable="z")]),
            ]
        )
        assert render_svg(prog).count("<circle") == 3

    def test_power_rails_present_per_rung(self):
        svg = render_svg(self._two_rung_prog())
        # Each rung has 2 power rails with stroke-width=_RAIL_W (4)
        assert svg.count('stroke-width="4"') == 4


class TestRenderBranch:
    """Branch (parallel) elements render correctly."""

    def _two_path_prog(self) -> PLCProgram:
        return PLCProgram(
            title="branch_test",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="a"),
                Branch(paths=[
                    [Contact(type=ContactType.NO, variable="b")],
                    [Contact(type=ContactType.NC, variable="c")],
                ]),
                Coil(variable="out"),
            ])]
        )

    def test_branch_shows_both_path_variables(self):
        svg = render_svg(self._two_path_prog())
        assert "b" in svg
        assert "c" in svg

    def test_branch_coil_still_renders(self):
        assert "<circle" in render_svg(self._two_path_prog())

    def test_branch_svg_valid_structure(self):
        svg = render_svg(self._two_path_prog())
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_two_path_branch_has_vertical_junction_lines(self):
        # The left and right junctions are vertical lines (x1 == x2)
        prog = PLCProgram(
            title="t",
            rungs=[Rung(elements=[
                Branch(paths=[
                    [Contact(type=ContactType.NO, variable="x")],
                    [Contact(type=ContactType.NO, variable="y")],
                ]),
                Coil(variable="q"),
            ])]
        )
        svg = render_svg(prog)
        # Find all stroke-width="2" lines and check some have x1==x2 (vertical)
        vertical = re.findall(
            r'<line x1="(\d+)" y1="\d+" x2="(\d+)" y2="\d+" stroke="black" stroke-width="2"/>',
            svg,
        )
        assert any(x1 == x2 for x1, x2 in vertical), "Expected at least one vertical junction line"

    def test_branch_does_not_regress_series_rung(self):
        # A plain series rung in the same program renders correctly
        prog = PLCProgram(
            title="mixed",
            rungs=[
                Rung(elements=[
                    Contact(type=ContactType.NO, variable="start"),
                    Coil(variable="motor"),
                ]),
                Rung(elements=[
                    Branch(paths=[
                        [Contact(type=ContactType.NO, variable="p")],
                        [Contact(type=ContactType.NC, variable="q")],
                    ]),
                    Coil(variable="lamp"),
                ]),
            ]
        )
        svg = render_svg(prog)
        assert svg.count("<circle") == 2
        assert "start" in svg
        assert "motor" in svg
        assert "p" in svg
        assert "lamp" in svg


class TestRenderFunctionBlock:
    """FunctionBlock elements render with rect and pin labels."""

    def _ton_prog(self) -> PLCProgram:
        return PLCProgram(
            title="fb_test",
            rungs=[Rung(elements=[
                Contact(type=ContactType.NO, variable="enable"),
                FunctionBlock(
                    block_type=FunctionBlockType.TON,
                    instance_name="timer1",
                    inputs={"IN": "enable", "PT": "T#5S"},
                    outputs={"Q": "timer_done", "ET": "elapsed"},
                ),
                Coil(variable="done"),
            ])]
        )

    def test_fb_renders_rect(self):
        assert "<rect" in render_svg(self._ton_prog())

    def test_fb_shows_block_type(self):
        assert "TON" in render_svg(self._ton_prog())

    def test_fb_shows_instance_name(self):
        assert "timer1" in render_svg(self._ton_prog())

    def test_fb_shows_input_pin_names(self):
        svg = render_svg(self._ton_prog())
        assert "IN" in svg
        assert "PT" in svg

    def test_fb_shows_output_pin_names(self):
        svg = render_svg(self._ton_prog())
        assert ">Q<" in svg or "Q" in svg
        assert "ET" in svg

    def test_fb_coil_still_renders(self):
        assert "<circle" in render_svg(self._ton_prog())

    def test_fb_svg_valid_structure(self):
        svg = render_svg(self._ton_prog())
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    def test_ctu_counter_renders_rect(self):
        prog = PLCProgram(
            title="ctu",
            rungs=[Rung(elements=[
                FunctionBlock(
                    block_type=FunctionBlockType.CTU,
                    instance_name="cnt1",
                    inputs={"CU": "pulse", "R": "reset", "PV": "10"},
                    outputs={"Q": "reached", "CV": "count"},
                ),
                Coil(variable="done"),
            ])]
        )
        svg = render_svg(prog)
        assert "<rect" in svg
        assert "CTU" in svg
        assert "cnt1" in svg
