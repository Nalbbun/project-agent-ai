from __future__ import annotations

import json
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .config import RouterConfigError, load_router_config
from .utils import delete_nested, get_nested, merged_generation

APP_NAME = "multi-agent-router"
DEFAULT_CONFIG_PATH = os.getenv(
    "ROUTER_CONFIG_PATH",
    "/app/configs/vllm_request_router.local.yaml",
)
ROUTER_BEARER_TOKEN = os.getenv("ROUTER_BEARER_TOKEN", "").strip()

app = FastAPI(title=APP_NAME, version="1.1.0")


@app.on_event("startup")
async def startup() -> None:
    try:
        app.state.router_config = load_router_config(DEFAULT_CONFIG_PATH)
    except RouterConfigError as exc:
        raise RuntimeError(str(exc)) from exc

    app.state.client = httpx.AsyncClient(follow_redirects=True)


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.client.aclose()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if ROUTER_BEARER_TOKEN:
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {ROUTER_BEARER_TOKEN}"
        if auth_header != expected:
            return JSONResponse(status_code=401, content={"error": {"message": "unauthorized"}})
    return await call_next(request)


def router_cfg() -> dict[str, Any]:
    return app.state.router_config


def get_role(request_json: dict[str, Any], request: Request) -> str | None:
    top_level = request_json.get("agent_role")
    if isinstance(top_level, str) and top_level.strip():
        return top_level.strip()
    cfg = router_cfg()
    fields = cfg["router"].get("request_role_fields", [])
    for path in fields:
        value = get_nested(request_json, path)
        if isinstance(value, str) and value.strip():
            return value.strip()
    header_role = request.headers.get("x-agent-role", "").strip()
    return header_role or None


def build_candidates(role: str) -> list[dict[str, Any]]:
    cfg = router_cfg()
    if role not in cfg["routes"]:
        return []
    route = cfg["routes"][role]
    candidates = [{
        "backend_name": route["backend"],
        "target_model": route.get("target_model"),
        "generation": route.get("generation", {}),
    }]
    for fb in route.get("fallback", []) or []:
        candidates.append({
            "backend_name": fb["backend"],
            "target_model": fb.get("target_model"),
            "generation": fb.get("generation", {}),
        })
    return candidates


def build_backend_headers(request: Request, backend_name: str, role: str, target_model: str | None) -> dict[str, str]:
    cfg = router_cfg()
    backend = cfg["backends"][backend_name]
    allowed = set(cfg["router"].get("propagate_headers", []))
    headers: dict[str, str] = {"content-type": "application/json"}
    for key, value in request.headers.items():
        if key.lower() in allowed:
            headers[key] = value
    api_key_env = backend.get("api_key_env")
    if api_key_env:
        api_key = os.getenv(api_key_env, "").strip()
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
    headers["x-router-role"] = role
    if target_model:
        headers["x-router-model"] = target_model
    headers.setdefault("x-request-id", str(uuid.uuid4()))
    return headers


async def parse_json(request: Request) -> dict[str, Any]:
    try:
        return await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"invalid json body: {exc}") from exc


def strip_router_fields(body: dict[str, Any]) -> dict[str, Any]:
    cfg = router_cfg()
    cleaned = json.loads(json.dumps(body))
    if not cfg["router"].get("policies", {}).get("strip_router_only_fields", True):
        return cleaned

    cleaned.pop("agent_role", None)
    for path in cfg["router"].get("request_role_fields", []):
        delete_nested(cleaned, path)
    for path in cfg["router"].get("request_task_fields", []):
        delete_nested(cleaned, path)
    return cleaned


def prepare_body(body: dict[str, Any], role: str, candidate: dict[str, Any]) -> dict[str, Any]:
    cfg = router_cfg()
    route_defaults = cfg["router"].get("default_generation", {})
    cleaned = strip_router_fields(body)
    generated = merged_generation(route_defaults, candidate.get("generation", {}), cleaned)
    generated["model"] = candidate["target_model"]

    metadata = generated.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.setdefault("router", {})
    metadata["router"].update(
        {
            "agent_role": role,
            "target_model": candidate["target_model"],
            "backend": candidate["backend_name"],
        }
    )
    metadata.setdefault("agent_role", role)
    generated["metadata"] = metadata
    generated.setdefault("extra_body", {})
    if isinstance(generated["extra_body"], dict):
        generated["extra_body"].setdefault("agent_role", role)
    return generated


def backend_url(backend_name: str, path: str) -> str:
    base = router_cfg()["backends"][backend_name]["base_url"].rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def backend_timeout(backend_name: str) -> httpx.Timeout:
    cfg = router_cfg()
    backend = cfg["backends"][backend_name]
    connect = backend.get(
        "connect_timeout_seconds",
        cfg["router"].get("default_connect_timeout_seconds", 10),
    )
    request_timeout = backend.get(
        "timeout_seconds",
        cfg["router"].get("default_request_timeout_seconds", 180),
    )
    return httpx.Timeout(connect=connect, read=request_timeout, write=request_timeout, pool=connect)


def backend_max_retries(backend_name: str) -> int:
    cfg = router_cfg()
    backend = cfg["backends"][backend_name]
    return int(backend.get("max_retries", 1))


async def try_non_stream(request: Request, path: str, role: str, body: dict[str, Any]) -> Response:
    client: httpx.AsyncClient = app.state.client
    errors: list[dict[str, Any]] = []

    for candidate in build_candidates(role):
        backend_name = candidate["backend_name"]
        prepared = prepare_body(body, role, candidate)
        url = backend_url(backend_name, path)
        for attempt in range(1, backend_max_retries(backend_name) + 1):
            headers = build_backend_headers(request, backend_name, role, candidate.get("target_model"))
            try:
                response = await client.post(url, headers=headers, json=prepared, timeout=backend_timeout(backend_name))
                if response.status_code >= 500:
                    errors.append({"backend": backend_name, "attempt": attempt, "status_code": response.status_code, "body": response.text[:1000]})
                    continue
                content_type = response.headers.get("content-type", "application/json")
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    media_type=content_type,
                    headers={
                        "x-router-role": role,
                        "x-router-backend": backend_name,
                        "x-router-model": candidate.get("target_model", ""),
                        "x-request-id": headers.get("x-request-id", ""),
                    },
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                errors.append({"backend": backend_name, "attempt": attempt, "error": repr(exc)})
                continue

    raise HTTPException(status_code=502, detail={"message": "all backends failed", "role": role, "errors": errors})


async def try_stream(request: Request, path: str, role: str, body: dict[str, Any]) -> StreamingResponse:
    client: httpx.AsyncClient = app.state.client
    errors: list[dict[str, Any]] = []

    for candidate in build_candidates(role):
        backend_name = candidate["backend_name"]
        prepared = prepare_body(body, role, candidate)
        url = backend_url(backend_name, path)
        for attempt in range(1, backend_max_retries(backend_name) + 1):
            headers = build_backend_headers(request, backend_name, role, candidate.get("target_model"))
            req = client.build_request("POST", url, headers=headers, json=prepared)
            try:
                response = await client.send(req, stream=True, timeout=backend_timeout(backend_name))
                if response.status_code >= 500:
                    errors.append({"backend": backend_name, "attempt": attempt, "status_code": response.status_code})
                    await response.aclose()
                    continue
                if response.status_code >= 400:
                    error_body = await response.aread()
                    await response.aclose()
                    return Response(
                        content=error_body,
                        status_code=response.status_code,
                        media_type=response.headers.get("content-type", "application/json"),
                        headers={"x-router-role": role, "x-router-backend": backend_name, "x-router-model": candidate.get("target_model", "")},
                    )

                async def iterator() -> Any:
                    try:
                        async for chunk in response.aiter_raw():
                            yield chunk
                    finally:
                        await response.aclose()

                return StreamingResponse(
                    iterator(),
                    status_code=response.status_code,
                    media_type=response.headers.get("content-type", "text/event-stream"),
                    headers={"x-router-role": role, "x-router-backend": backend_name, "x-router-model": candidate.get("target_model", "")},
                )
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                errors.append({"backend": backend_name, "attempt": attempt, "error": repr(exc)})
                continue

    raise HTTPException(status_code=502, detail={"message": "all backends failed", "role": role, "errors": errors})


@app.get("/health")
async def health() -> dict[str, Any]:
    cfg = router_cfg()
    client: httpx.AsyncClient = app.state.client
    results: dict[str, Any] = {"status": "ok", "router": cfg.get("router", {}).get("name", APP_NAME), "backends": {}}
    overall_ok = True

    for backend_name, backend in cfg["backends"].items():
        health_url = backend.get("health_url")
        if not health_url:
            results["backends"][backend_name] = {"status": "unknown", "detail": "no health_url configured"}
            continue
        try:
            resp = await client.get(health_url, timeout=backend_timeout(backend_name))
            ok = resp.status_code < 400
            overall_ok &= ok
            results["backends"][backend_name] = {"status": "ok" if ok else "error", "status_code": resp.status_code}
        except Exception as exc:  # noqa: BLE001
            overall_ok = False
            results["backends"][backend_name] = {"status": "error", "detail": repr(exc)}

    if not overall_ok:
        results["status"] = "degraded"
    return results


@app.get("/router/routes")
async def list_routes() -> dict[str, Any]:
    cfg = router_cfg()
    return {
        "router": cfg.get("router", {}).get("name", APP_NAME),
        "roles": sorted(cfg["routes"].keys()),
        "routes": cfg["routes"],
    }


@app.get("/router/decision")
async def route_decision(role: str) -> dict[str, Any]:
    return {"role": role, "candidates": build_candidates(role)}


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    cfg = router_cfg()
    now = 0
    items = [{"id": "router-auto", "object": "model", "created": now, "owned_by": APP_NAME}]
    seen = {"router-auto"}

    for role, route in cfg["routes"].items():
        target_model = route.get("target_model")
        if target_model and target_model not in seen:
            items.append({
                "id": target_model,
                "object": "model",
                "created": now,
                "owned_by": APP_NAME,
                "metadata": {"agent_role": role, "backend": route.get("backend")},
            })
            seen.add(target_model)
        for fb in route.get("fallback", []) or []:
            fb_model = fb.get("target_model")
            if fb_model and fb_model not in seen:
                items.append({
                    "id": fb_model,
                    "object": "model",
                    "created": now,
                    "owned_by": APP_NAME,
                    "metadata": {"agent_role": role, "backend": fb.get("backend")},
                })
                seen.add(fb_model)
    return {"object": "list", "data": items}


async def handle_proxy(request: Request, path: str) -> Response:
    cfg = router_cfg()
    body = await parse_json(request)
    role = get_role(body, request)
    if not role:
        message = cfg["router"].get("policies", {}).get(
            "missing_role_message", "agent_role is required"
        )
        raise HTTPException(status_code=400, detail=message)
    if role not in cfg["routes"]:
        unknown_action = cfg["router"].get("policies", {}).get("unknown_role_action", "reject")
        if unknown_action == "reject":
            raise HTTPException(status_code=400, detail=f"unknown agent_role: {role}")
    if body.get("stream") is True:
        return await try_stream(request, path, role, body)
    return await try_non_stream(request, path, role, body)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    return await handle_proxy(request, "/chat/completions")


@app.post("/v1/completions")
async def completions(request: Request) -> Response:
    return await handle_proxy(request, "/completions")


@app.post("/v1/responses")
async def responses(request: Request) -> Response:
    return await handle_proxy(request, "/responses")
