---
Status: done
---

# 03 — LLM 生成器——串联 Rung（litellm + PydanticAI，mock 测试）

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

实现核心生成器：接受自然语言描述 + 品牌 + LLM 选型，调用 LLM，返回结构化 `PLCProgram`（含 LD 数据 + ST 文本副本）。

关键设计：
- litellm 统一调用接口，模型名通过参数传入（默认 `claude-sonnet-4-6`，支持 OpenAI 模型）
- PydanticAI 强制 LLM 输出符合 `PLCProgram` schema 的 JSON
- System Prompt 注入 IEC 61131-3 规范、安全约束（急停联锁不可绕过）、变量命名规范
- LLM 一次请求同时输出 LD 结构和 `st_code` 字段
- 描述不足或无法生成合法逻辑时，返回结构化错误而非空/无效 `PLCProgram`

测试使用 mock LLM 响应，不调用真实 API，覆盖：正常生成、描述不足返回错误、LLM 返回非法 schema 时的重试/报错路径。

## Acceptance criteria

- [ ] 传入合法描述时返回有效 `PLCProgram` 对象
- [ ] 返回的 `PLCProgram` 通过 LD 验证器（Issue 02）的检验
- [ ] 传入模糊描述时返回结构化错误，不返回空 `PLCProgram`
- [ ] 支持通过参数切换 Claude / OpenAI 模型
- [ ] 通过环境变量读取 `ANTHROPIC_API_KEY` 和 `OPENAI_API_KEY`
- [ ] mock 测试全部通过，不调用真实 LLM API

## Blocked by

- `issues/01-ld-data-model.md`
