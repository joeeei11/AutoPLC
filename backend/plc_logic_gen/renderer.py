"""SVG renderer for IEC 61131-3 Ladder Diagram programs."""

from __future__ import annotations

from plc_logic_gen.models.ld import (
    Branch,
    Coil,
    Contact,
    ContactType,
    FunctionBlock,
    PLCProgram,
    RungElement,
)

# Layout constants (pixels)
_ELEM_W = 80        # width of each contact/coil slot
_ELEM_H = 40        # height of element symbol area
_WIRE_Y = 20        # wire y-offset from element/rung top (vertical centre)
_RAIL_X = 20        # x of power rails
_RAIL_MARGIN = 20   # gap between rail and first/last element slot
_RAIL_W = 4         # stroke-width of power rails
_LABEL_DY = 14      # label baseline offset below element bottom
_RUNG_GAP = 12      # vertical gap between rung rows
_PATH_GAP = 10      # gap between parallel paths in a branch

_FB_W = 120         # function block slot width
_FB_HEADER_H = 26   # height of the type + instance header row inside the FB
_FB_PIN_H = 18      # height per pin row


def _contact_svg(x: int, y: int, contact: Contact) -> list[str]:
    wy = y + _WIRE_Y
    bar_top = y + 6
    bar_bot = y + _ELEM_H - 6
    bar_x1 = x + 26
    bar_x2 = x + 54

    parts = [
        f'<line x1="{x}" y1="{wy}" x2="{bar_x1}" y2="{wy}" stroke="black" stroke-width="2"/>',
        f'<line x1="{bar_x1}" y1="{bar_top}" x2="{bar_x1}" y2="{bar_bot}" stroke="black" stroke-width="2"/>',
        f'<line x1="{bar_x2}" y1="{bar_top}" x2="{bar_x2}" y2="{bar_bot}" stroke="black" stroke-width="2"/>',
        f'<line x1="{bar_x2}" y1="{wy}" x2="{x + _ELEM_W}" y2="{wy}" stroke="black" stroke-width="2"/>',
    ]
    if contact.type == ContactType.NC:
        parts.append(
            f'<line x1="{bar_x1}" y1="{bar_bot}" x2="{bar_x2}" y2="{bar_top}"'
            f' stroke="black" stroke-width="2"/>'
        )
    label_x = x + _ELEM_W // 2
    label_y = y + _ELEM_H + _LABEL_DY
    parts.append(
        f'<text x="{label_x}" y="{label_y}" text-anchor="middle"'
        f' font-family="monospace" font-size="12">{contact.variable}</text>'
    )
    return parts


def _coil_svg(x: int, y: int, coil: Coil) -> list[str]:
    wy = y + _WIRE_Y
    cx = x + _ELEM_W // 2
    r = 12

    parts = [
        f'<line x1="{x}" y1="{wy}" x2="{cx - r}" y2="{wy}" stroke="black" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{wy}" r="{r}" fill="none" stroke="black" stroke-width="2"/>',
        f'<line x1="{cx + r}" y1="{wy}" x2="{x + _ELEM_W}" y2="{wy}" stroke="black" stroke-width="2"/>',
    ]
    label_x = cx
    label_y = y + _ELEM_H + _LABEL_DY
    parts.append(
        f'<text x="{label_x}" y="{label_y}" text-anchor="middle"'
        f' font-family="monospace" font-size="12">{coil.variable}</text>'
    )
    return parts


def _function_block_svg(x: int, y: int, fb: FunctionBlock) -> list[str]:
    n_pins = max(len(fb.inputs), len(fb.outputs), 1)
    fb_h = _FB_HEADER_H + n_pins * _FB_PIN_H
    wy = y + _WIRE_Y
    rect_x = x + 8
    rect_w = _FB_W - 16

    parts = [
        f'<line x1="{x}" y1="{wy}" x2="{rect_x}" y2="{wy}" stroke="black" stroke-width="2"/>',
        f'<line x1="{rect_x + rect_w}" y1="{wy}" x2="{x + _FB_W}" y2="{wy}" stroke="black" stroke-width="2"/>',
        f'<rect x="{rect_x}" y="{y}" width="{rect_w}" height="{fb_h}"'
        f' fill="white" stroke="black" stroke-width="2" rx="3"/>',
        f'<text x="{x + _FB_W // 2}" y="{y + 14}" text-anchor="middle"'
        f' font-family="monospace" font-size="11" font-weight="bold">{fb.block_type.value}</text>',
        f'<text x="{x + _FB_W // 2}" y="{y + 24}" text-anchor="middle"'
        f' font-family="monospace" font-size="10">{fb.instance_name}</text>',
    ]

    for i, pin_name in enumerate(fb.inputs):
        pin_y = y + _FB_HEADER_H + i * _FB_PIN_H + _FB_PIN_H // 2
        parts.append(
            f'<text x="{rect_x + 4}" y="{pin_y + 4}"'
            f' font-family="monospace" font-size="9">{pin_name}</text>'
        )

    for i, pin_name in enumerate(fb.outputs):
        pin_y = y + _FB_HEADER_H + i * _FB_PIN_H + _FB_PIN_H // 2
        parts.append(
            f'<text x="{rect_x + rect_w - 4}" y="{pin_y + 4}" text-anchor="end"'
            f' font-family="monospace" font-size="9">{pin_name}</text>'
        )

    return parts


def _elem_x_advance(elem: RungElement) -> int:
    if isinstance(elem, FunctionBlock):
        return _FB_W
    if isinstance(elem, Branch):
        return _branch_x_width(elem)
    return _ELEM_W


def _branch_x_width(branch: Branch) -> int:
    return max(sum(_elem_x_advance(e) for e in path) for path in branch.paths)


def _branch_svg(branch_x: int, rung_y: int, branch: Branch) -> tuple[list[str], int]:
    """Return (svg_parts, x_advance) for a parallel branch."""
    n_paths = len(branch.paths)
    branch_width = _branch_x_width(branch)
    right_x = branch_x + branch_width

    top_wire_y = rung_y + _WIRE_Y
    bot_wire_y = rung_y + (n_paths - 1) * (_ELEM_H + _PATH_GAP) + _WIRE_Y

    parts: list[str] = [
        f'<line x1="{branch_x}" y1="{top_wire_y}" x2="{branch_x}" y2="{bot_wire_y}"'
        f' stroke="black" stroke-width="2"/>',
        f'<line x1="{right_x}" y1="{top_wire_y}" x2="{right_x}" y2="{bot_wire_y}"'
        f' stroke="black" stroke-width="2"/>',
    ]

    for i, path in enumerate(branch.paths):
        path_y = rung_y + i * (_ELEM_H + _PATH_GAP)
        path_wire_y = path_y + _WIRE_Y
        px = branch_x

        for elem in path:
            if isinstance(elem, Contact):
                parts.extend(_contact_svg(px, path_y, elem))
                px += _ELEM_W
            elif isinstance(elem, Coil):
                parts.extend(_coil_svg(px, path_y, elem))
                px += _ELEM_W
            elif isinstance(elem, FunctionBlock):
                parts.extend(_function_block_svg(px, path_y, elem))
                px += _FB_W
            elif isinstance(elem, Branch):
                sub_parts, sub_w = _branch_svg(px, path_y, elem)
                parts.extend(sub_parts)
                px += sub_w

        # Horizontal fill wire if path is shorter than branch_width
        if px < right_x:
            parts.append(
                f'<line x1="{px}" y1="{path_wire_y}" x2="{right_x}" y2="{path_wire_y}"'
                f' stroke="black" stroke-width="2"/>'
            )

    return parts, branch_width


def _rung_height(rung) -> int:
    """Total symbol height for a rung (accounts for branches and FBs)."""
    max_h = _ELEM_H
    for elem in rung.elements:
        if isinstance(elem, Branch):
            n = len(elem.paths)
            bh = n * _ELEM_H + (n - 1) * _PATH_GAP
            max_h = max(max_h, bh)
        elif isinstance(elem, FunctionBlock):
            n_pins = max(len(elem.inputs), len(elem.outputs), 1)
            fh = _FB_HEADER_H + n_pins * _FB_PIN_H
            max_h = max(max_h, fh)
    return max_h


def _rung_svg(rung, y: int, svg_width: int) -> list[str]:
    parts: list[str] = []
    wy = y + _WIRE_Y
    rung_h = _rung_height(rung)
    left_rail_x = _RAIL_X
    right_rail_x = svg_width - _RAIL_X

    parts.append(
        f'<line x1="{left_rail_x}" y1="{y}" x2="{left_rail_x}" y2="{y + rung_h}"'
        f' stroke="black" stroke-width="{_RAIL_W}"/>'
    )
    parts.append(
        f'<line x1="{right_rail_x}" y1="{y}" x2="{right_rail_x}" y2="{y + rung_h}"'
        f' stroke="black" stroke-width="{_RAIL_W}"/>'
    )

    elem_start_x = left_rail_x + _RAIL_MARGIN
    parts.append(
        f'<line x1="{left_rail_x}" y1="{wy}" x2="{elem_start_x}" y2="{wy}"'
        f' stroke="black" stroke-width="2"/>'
    )

    x = elem_start_x
    for elem in rung.elements:
        if isinstance(elem, Contact):
            parts.extend(_contact_svg(x, y, elem))
            x += _ELEM_W
        elif isinstance(elem, Coil):
            parts.extend(_coil_svg(x, y, elem))
            x += _ELEM_W
        elif isinstance(elem, FunctionBlock):
            parts.extend(_function_block_svg(x, y, elem))
            x += _FB_W
        elif isinstance(elem, Branch):
            branch_parts, branch_w = _branch_svg(x, y, elem)
            parts.extend(branch_parts)
            x += branch_w

    parts.append(
        f'<line x1="{x}" y1="{wy}" x2="{right_rail_x}" y2="{wy}"'
        f' stroke="black" stroke-width="2"/>'
    )
    return parts


def render_svg(program: PLCProgram) -> str:
    """Render a PLCProgram to an SVG string."""
    if not program.rungs:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"></svg>'

    max_x_advance = max(
        sum(_elem_x_advance(e) for e in rung.elements)
        for rung in program.rungs
    )
    svg_width = _RAIL_X + _RAIL_MARGIN + max_x_advance + _RAIL_MARGIN + _RAIL_X

    # Compute y-top for each rung dynamically (height varies for branches/FBs)
    rung_tops: list[int] = []
    cursor_y = _RUNG_GAP
    for rung in program.rungs:
        rung_tops.append(cursor_y)
        cursor_y += _rung_height(rung) + _LABEL_DY + 8 + _RUNG_GAP

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{cursor_y}">']
    for rung, y in zip(program.rungs, rung_tops):
        lines.extend(_rung_svg(rung, y, svg_width))
    lines.append('</svg>')
    return "\n".join(lines)
