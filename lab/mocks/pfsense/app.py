#!/usr/bin/env python3
"""Minimal pfSense API v1 stub for local lab and CI."""

from fastapi import FastAPI, Request

app = FastAPI(title="pfSense API Mock")
_rules: list[dict] = []


def _ok(data=None):
    return {
        "status": "ok",
        "code": 200,
        "return_code": 0,
        "message": "ok",
        "data": data if data is not None else {},
    }


@app.get("/api/v1/status/system")
def system_status():
    return _ok({"status": "online", "mock": True})


@app.get("/api/v1/firewall/rule")
def list_rules():
    return _ok(_rules)


@app.post("/api/v1/firewall/rule")
async def create_rule(request: Request):
    payload = await request.json()
    _rules.append(payload)
    return _ok(payload)


@app.post("/api/v1/firewall/apply")
async def apply_changes():
    return _ok({"applied": True})


@app.get("/health")
def health():
    return {"status": "healthy"}
