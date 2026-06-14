/**
 * 5 个预置 Demo 场景数据（不需要 LLM，直接加载）
 */

import type { PLCProgram } from "./api";

export interface DemoScene {
  label: string;
  description: string;
  program: PLCProgram;
}

export const DEMO_SCENES: DemoScene[] = [
  {
    label: "电机启停",
    description: "电机启停控制：启动按钮（NO）+ 自保持 + 停止按钮（NC）+ 电机线圈",
    program: {
      title: "电机启停控制",
      description: "启动按钮（NO）+ 自保持 + 停止按钮（NC）控制电机线圈",
      variables: [
        { name: "start_btn", data_type: "BOOL" },
        { name: "stop_btn",  data_type: "BOOL" },
        { name: "motor_run", data_type: "BOOL" },
      ],
      rungs: [
        {
          elements: [
            {
              paths: [
                [{ type: "NO", variable: "start_btn" }],
                [{ type: "NO", variable: "motor_run" }],
              ],
            },
            { type: "NC", variable: "stop_btn" },
            { variable: "motor_run", negated: false },
          ],
        },
      ],
      st_code:
        "IF (start_btn OR motor_run) AND NOT stop_btn THEN\n" +
        "  motor_run := TRUE;\n" +
        "ELSE\n" +
        "  motor_run := FALSE;\n" +
        "END_IF",
    },
  },

  {
    label: "传送带计数",
    description: "传送带物料计数：光电传感器触发 CTU 计数器，满载（计数 ≥ 10）时停止传送带",
    program: {
      title: "传送带物料计数",
      description: "光电传感器触发 CTU 计数器，满载（计数 ≥ 10）时停止传送带",
      variables: [
        { name: "photo_sensor", data_type: "BOOL" },
        { name: "count_reset",  data_type: "BOOL" },
        { name: "belt_run",     data_type: "BOOL" },
        { name: "count_done",   data_type: "BOOL" },
        { name: "count_active", data_type: "BOOL" },
      ],
      rungs: [
        {
          elements: [
            { type: "NO", variable: "photo_sensor" },
            {
              block_type: "CTU",
              instance_name: "cnt",
              inputs:  { CU: "photo_sensor", R: "count_reset", PV: "10" },
              outputs: { Q: "count_done", CV: "count_val" },
            },
            { variable: "count_active", negated: false },
          ],
        },
        {
          elements: [
            { type: "NC", variable: "count_done" },
            { variable: "belt_run", negated: false },
          ],
        },
      ],
      st_code:
        "cnt(CU := photo_sensor, R := count_reset, PV := 10);\n" +
        "count_done := cnt.Q;\n" +
        "IF NOT count_done THEN belt_run := TRUE;\n" +
        "ELSE belt_run := FALSE; END_IF",
    },
  },

  {
    label: "PID 温控",
    description: "PID 温控回路（简化版）：温度传感器比较块 + 加热线圈开关逻辑",
    program: {
      title: "PID 温控回路",
      description: "温度传感器比较块 + 加热线圈开关逻辑（简化 PID）",
      variables: [
        { name: "heat_enable", data_type: "BOOL" },
        { name: "temp_high",   data_type: "BOOL" },
        { name: "heater_on",   data_type: "BOOL" },
        { name: "pid_active",  data_type: "BOOL" },
      ],
      rungs: [
        {
          elements: [
            { type: "NO", variable: "heat_enable" },
            {
              block_type: "PID",
              instance_name: "temp_pid",
              inputs:  { PV: "temp_sensor", SP: "80.0", KP: "1.0" },
              outputs: { OUT: "heat_output" },
            },
            { variable: "pid_active", negated: false },
          ],
        },
        {
          elements: [
            { type: "NO", variable: "heat_enable" },
            { type: "NC", variable: "temp_high" },
            { variable: "heater_on", negated: false },
          ],
        },
      ],
      st_code:
        "IF heat_enable THEN\n" +
        "  temp_pid(PV := temp_sensor, SP := 80.0);\n" +
        "  pid_active := TRUE;\n" +
        "END_IF\n" +
        "heater_on := heat_enable AND NOT temp_high;",
    },
  },

  {
    label: "急停联锁",
    description: "急停安全联锁：多点急停（NC）串联 + 运行使能线圈，急停优先于启动",
    program: {
      title: "急停安全联锁",
      description: "多点急停（NC）串联 + 运行使能线圈，急停优先于启动",
      variables: [
        { name: "start_btn",  data_type: "BOOL" },
        { name: "e_stop1",    data_type: "BOOL" },
        { name: "e_stop2",    data_type: "BOOL" },
        { name: "run_enable", data_type: "BOOL" },
      ],
      rungs: [
        {
          elements: [
            { type: "NO", variable: "start_btn" },
            { type: "NC", variable: "e_stop1" },
            { type: "NC", variable: "e_stop2" },
            { variable: "run_enable", negated: false },
          ],
        },
      ],
      st_code:
        "IF start_btn AND NOT e_stop1 AND NOT e_stop2 THEN\n" +
        "  run_enable := TRUE;\n" +
        "ELSE\n" +
        "  run_enable := FALSE;\n" +
        "END_IF",
    },
  },

  {
    label: "液位控制",
    description: "液位控制：高位传感器（NC）+ 低位传感器（NO）控制水泵启停",
    program: {
      title: "液位控制",
      description: "高位传感器（NC）+ 低位传感器（NO）控制水泵启停",
      variables: [
        { name: "level_high", data_type: "BOOL" },
        { name: "level_low",  data_type: "BOOL" },
        { name: "pump_run",   data_type: "BOOL" },
      ],
      rungs: [
        {
          elements: [
            {
              paths: [
                [{ type: "NO", variable: "level_low" }],
                [{ type: "NO", variable: "pump_run" }],
              ],
            },
            { type: "NC", variable: "level_high" },
            { variable: "pump_run", negated: false },
          ],
        },
      ],
      st_code:
        "IF (level_low OR pump_run) AND NOT level_high THEN\n" +
        "  pump_run := TRUE;\n" +
        "ELSE\n" +
        "  pump_run := FALSE;\n" +
        "END_IF",
    },
  },
];
