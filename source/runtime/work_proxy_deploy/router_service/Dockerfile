FROM python:3.11-slim

WORKDIR /app
COPY router_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY router_service/app /app/router_service/app
COPY configs /app/configs

ENV PYTHONPATH=/app \
    ROUTER_CONFIG_PATH=/app/configs/vllm_request_router.local.yaml \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8080

EXPOSE 8080
CMD ["uvicorn", "router_service.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
