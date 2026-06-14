---
Status: ready-for-agent
---

# 05 — FastAPI 后端基础——`/generate` + `/validate` 端点

## Parent

`.scratch/plc-logic-gen/PRD.md`

## What to build

搭建 FastAPI 后端，实现两个核心端点，将生成器、验证器、SVG 渲染器串联起来，形成第一个可通过 HTTP 调用的完整路径。

端点契约：

`POST /api/generate`
- 请求体：`{ description: string, brand: "generic"|"siemens"|"rockwell", llm: "claude"|"openai" }`
- 成功响应：`{ plc_program: PLCProgram, svg: string }`
- 失败响应：`{ error: string }`

`POST /api/validate`
- 请求体：`{ plc_program: PLCProgram }`
- 响应：`{ errors: ValidationError[] }`（空列表表示合法）

同时配置 CORS（允许前端本地开发调用）和环境变量加载。

## Acceptance criteria

- [ ] `POST /api/generate` 传入合法描述时返回 `plc_program` + `svg`
- [ ] `POST /api/generate` 传入模糊描述时返回 `error` 字段
- [ ] `POST /api/validate` 传入合法 `PLCProgram` 时返回空 `errors` 列表
- [ ] `POST /api/validate` 传入非法 `PLCProgram` 时返回具体错误信息
- [ ] 服务启动后 `/docs` 可访问 Swagger UI
- [ ] CORS 配置允许本地前端（`http://localhost:5173`）访问

## Blocked by

- `issues/02-ld-validator.md`
- `issues/03-llm-generator-basic.md`
- `issues/04-svg-renderer-phase1.md`
