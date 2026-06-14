"""Tests for 5 Demo scene PLCPrograms — all must pass the LD validator (Issue 14)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from plc_logic_gen.api import app
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
from plc_logic_gen.validator import validate_program

client = TestClient(app)


# ---------------------------------------------------------------------------
# 构造 5 个 Demo 场景
# ---------------------------------------------------------------------------

def _demo1_motor_start_stop() -> PLCProgram:
    """电机启停控制：启动按钮（NO）+ 自保持 + 停止按钮（NC）+ 电机线圈"""
    return PLCProgram(
        title="电机启停控制",
        description="启动按钮（NO）+ 自保持 + 停止按钮（NC）控制电机线圈",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="stop_btn", data_type=DataType.BOOL),
            Variable(name="motor_run", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Branch(paths=[
                        [Contact(type=ContactType.NO, variable="start_btn")],
                        [Contact(type=ContactType.NO, variable="motor_run")],
                    ]),
                    Contact(type=ContactType.NC, variable="stop_btn"),
                    Coil(variable="motor_run"),
                ],
                comment="启动或自保持，停止按钮串联",
            )
        ],
        st_code=(
            "IF (start_btn OR motor_run) AND NOT stop_btn THEN\n"
            "  motor_run := TRUE;\n"
            "ELSE\n"
            "  motor_run := FALSE;\n"
            "END_IF"
        ),
    )


def _demo2_conveyor_counter() -> PLCProgram:
    """传送带物料计数：光电传感器触发 CTU，满载停止传送带"""
    return PLCProgram(
        title="传送带物料计数",
        description="光电传感器触发 CTU 计数器，满载（计数 ≥ 10）时停止传送带",
        variables=[
            Variable(name="photo_sensor", data_type=DataType.BOOL),
            Variable(name="count_reset", data_type=DataType.BOOL),
            Variable(name="belt_run", data_type=DataType.BOOL),
            Variable(name="count_done", data_type=DataType.BOOL),
            Variable(name="count_active", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="photo_sensor"),
                    FunctionBlock(
                        block_type=FunctionBlockType.CTU,
                        instance_name="cnt",
                        inputs={"CU": "photo_sensor", "R": "count_reset", "PV": "10"},
                        outputs={"Q": "count_done", "CV": "count_val"},
                    ),
                    Coil(variable="count_active"),
                ],
                comment="CTU 计数传感器脉冲",
            ),
            Rung(
                elements=[
                    Contact(type=ContactType.NC, variable="count_done"),
                    Coil(variable="belt_run"),
                ],
                comment="未满载时传送带运行",
            ),
        ],
        st_code=(
            "cnt(CU := photo_sensor, R := count_reset, PV := 10);\n"
            "count_done := cnt.Q;\n"
            "count_active := photo_sensor;\n"
            "IF NOT count_done THEN belt_run := TRUE;\n"
            "ELSE belt_run := FALSE; END_IF"
        ),
    )


def _demo3_pid_temperature() -> PLCProgram:
    """PID 温控回路（简化版）：温度比较 + 加热线圈开关逻辑"""
    return PLCProgram(
        title="PID 温控回路",
        description="温度传感器比较块 + 加热线圈开关逻辑（简化 PID）",
        variables=[
            Variable(name="heat_enable", data_type=DataType.BOOL),
            Variable(name="temp_high", data_type=DataType.BOOL),
            Variable(name="heater_on", data_type=DataType.BOOL),
            Variable(name="pid_active", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="heat_enable"),
                    FunctionBlock(
                        block_type=FunctionBlockType.PID,
                        instance_name="temp_pid",
                        inputs={"PV": "temp_sensor", "SP": "80.0", "KP": "1.0"},
                        outputs={"OUT": "heat_output"},
                    ),
                    Coil(variable="pid_active"),
                ],
                comment="PID 控制器使能",
            ),
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="heat_enable"),
                    Contact(type=ContactType.NC, variable="temp_high"),
                    Coil(variable="heater_on"),
                ],
                comment="启用且温度未过高时加热",
            ),
        ],
        st_code=(
            "IF heat_enable THEN\n"
            "  temp_pid(PV := temp_sensor, SP := 80.0);\n"
            "  pid_active := TRUE;\n"
            "END_IF\n"
            "heater_on := heat_enable AND NOT temp_high;"
        ),
    )


def _demo4_emergency_stop() -> PLCProgram:
    """急停安全联锁：多点急停（NC）串联 + 运行使能线圈"""
    return PLCProgram(
        title="急停安全联锁",
        description="多点急停（NC）串联 + 运行使能线圈，急停优先于启动",
        variables=[
            Variable(name="start_btn", data_type=DataType.BOOL),
            Variable(name="e_stop1", data_type=DataType.BOOL),
            Variable(name="e_stop2", data_type=DataType.BOOL),
            Variable(name="run_enable", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Contact(type=ContactType.NO, variable="start_btn"),
                    Contact(type=ContactType.NC, variable="e_stop1"),
                    Contact(type=ContactType.NC, variable="e_stop2"),
                    Coil(variable="run_enable"),
                ],
                comment="启动且两路急停均未触发",
            )
        ],
        st_code=(
            "IF start_btn AND NOT e_stop1 AND NOT e_stop2 THEN\n"
            "  run_enable := TRUE;\n"
            "ELSE\n"
            "  run_enable := FALSE;\n"
            "END_IF"
        ),
    )


def _demo5_level_control() -> PLCProgram:
    """液位控制：高位传感器（NC）+ 低位传感器（NO）控制水泵启停"""
    return PLCProgram(
        title="液位控制",
        description="高位传感器（NC）+ 低位传感器（NO）控制水泵启停",
        variables=[
            Variable(name="level_high", data_type=DataType.BOOL),
            Variable(name="level_low", data_type=DataType.BOOL),
            Variable(name="pump_run", data_type=DataType.BOOL),
        ],
        rungs=[
            Rung(
                elements=[
                    Branch(paths=[
                        [Contact(type=ContactType.NO, variable="level_low")],
                        [Contact(type=ContactType.NO, variable="pump_run")],
                    ]),
                    Contact(type=ContactType.NC, variable="level_high"),
                    Coil(variable="pump_run"),
                ],
                comment="低位启动或自保持，高位停止",
            )
        ],
        st_code=(
            "IF (level_low OR pump_run) AND NOT level_high THEN\n"
            "  pump_run := TRUE;\n"
            "ELSE\n"
            "  pump_run := FALSE;\n"
            "END_IF"
        ),
    )


ALL_DEMOS = [
    _demo1_motor_start_stop,
    _demo2_conveyor_counter,
    _demo3_pid_temperature,
    _demo4_emergency_stop,
    _demo5_level_control,
]


# ---------------------------------------------------------------------------
# 验证器测试
# ---------------------------------------------------------------------------

class TestDemoValidation:
    """所有 Demo 场景均通过 LD 验证器。"""

    def test_demo1_motor_passes_validator(self):
        assert validate_program(_demo1_motor_start_stop()) == []

    def test_demo2_conveyor_passes_validator(self):
        assert validate_program(_demo2_conveyor_counter()) == []

    def test_demo3_pid_passes_validator(self):
        assert validate_program(_demo3_pid_temperature()) == []

    def test_demo4_estop_passes_validator(self):
        assert validate_program(_demo4_emergency_stop()) == []

    def test_demo5_level_passes_validator(self):
        assert validate_program(_demo5_level_control()) == []

    def test_demo4_estop_contacts_are_nc(self):
        """急停触点必须为 NC 类型。"""
        prog = _demo4_emergency_stop()
        estop_contacts = [
            elem
            for rung in prog.rungs
            for elem in rung.elements
            if isinstance(elem, Contact) and "e_stop" in elem.variable
        ]
        assert len(estop_contacts) == 2
        for c in estop_contacts:
            assert c.type == ContactType.NC, f"{c.variable} must be NC"


# ---------------------------------------------------------------------------
# /api/render 端点测试
# ---------------------------------------------------------------------------

class TestRenderEndpoint:
    """POST /api/render 返回有效 SVG。"""

    def _render(self, prog: PLCProgram) -> dict:
        return client.post(
            "/api/render",
            json={"plc_program": prog.model_dump()},
        )

    def test_render_returns_200(self):
        res = self._render(_demo1_motor_start_stop())
        assert res.status_code == 200

    def test_render_returns_svg_field(self):
        res = self._render(_demo1_motor_start_stop())
        assert "svg" in res.json()

    def test_render_svg_starts_with_svg_tag(self):
        res = self._render(_demo1_motor_start_stop())
        assert res.json()["svg"].startswith("<svg")

    def test_all_demos_render_successfully(self):
        for fn in ALL_DEMOS:
            res = self._render(fn())
            assert res.status_code == 200, f"{fn.__name__} render failed"
            assert res.json()["svg"].startswith("<svg")
