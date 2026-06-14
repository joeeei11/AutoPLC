FROM python:3.11-slim

WORKDIR /app

# 安装依赖（独立层，pyproject.toml 不变时利用缓存）
RUN pip install --no-cache-dir \
    "pydantic>=2.7" \
    "pydantic-ai[anthropic]>=0.0.49" \
    "openai>=1.0" \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.29" \
    "python-dotenv>=1.0" \
    "httpx>=0.27"

COPY plc_logic_gen/ ./plc_logic_gen/
COPY main.py .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "plc_logic_gen.api:app", "--host", "0.0.0.0", "--port", "8000"]
