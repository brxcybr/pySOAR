#!/usr/bin/env python3
"""Minimal CrowdSec LAPI mock."""

from fastapi import FastAPI, Request

app = FastAPI(title="CrowdSec LAPI Mock")
_decisions: list[dict] = []


@app.get("/v1/decisions")
def list_decisions():
    return _decisions


@app.post("/v1/decisions")
async def create_decision(request: Request):
    payload = await request.json()
    _decisions.append(payload)
    return payload


@app.delete("/v1/decisions/{value}")
def delete_decision(value: str):
    global _decisions
    _decisions = [d for d in _decisions if d.get("value") != value]
    return {"deleted": value}


@app.get("/health")
def health():
    return {"status": "healthy"}
