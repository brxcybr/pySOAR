#!/usr/bin/env python3
"""Webhook sink for lab testing — logs incoming POST payloads."""

from fastapi import FastAPI, Request

app = FastAPI(title="Webhook Sink")
_received: list[dict] = []


@app.post("/{path:path}")
async def receive_path(path: str, request: Request):
    return await _store(path, request)


@app.post("/")
async def receive_root(request: Request):
    return await _store("", request)


async def _store(path: str, request: Request):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        body = await request.json()
    else:
        body = (await request.body()).decode("utf-8", errors="replace")
    entry = {"path": path or "/", "body": body}
    _received.append(entry)
    return {"status": "received", "count": len(_received)}


@app.get("/health")
def health():
    return {"status": "healthy", "received": len(_received)}


@app.get("/messages")
def messages():
    return _received
