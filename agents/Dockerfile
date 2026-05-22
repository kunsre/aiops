FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    langgraph \
    langchain-anthropic \
    langchain-core \
    pydantic \
    fastapi \
    uvicorn \
    httpx \
    pygithub \
    rich \
    anthropic

COPY src/ src/
ENV PYTHONPATH=/app/src

EXPOSE 9090

CMD ["uvicorn", "aiops_agents.webhooks.alertmanager:app", "--host", "0.0.0.0", "--port", "9090"]
