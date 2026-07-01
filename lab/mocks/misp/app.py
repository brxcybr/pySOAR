#!/usr/bin/env python3
"""Minimal MISP API mock for lab HTTP testing."""

from fastapi import FastAPI

app = FastAPI(title="MISP API Mock")

MOCK_ATTRIBUTES = [
    {"type": "ip-dst", "value": "203.0.113.10"},
    {"type": "ip-dst", "value": "203.0.113.20"},
    {"type": "domain", "value": "malicious.example.com"},
]


@app.get("/servers/getVersion")
def version():
    return {"version": "2.4.190-mock", "mock": True}


@app.get("/feeds/index")
def feeds():
    return [
        {
            "Feed": {
                "id": "1",
                "name": "firehol_level1",
                "enabled": True,
                "event_id": "1",
            }
        }
    ]


@app.get("/attributes/restSearch")
def rest_search():
    return {"response": {"Attribute": MOCK_ATTRIBUTES}}


@app.get("/health")
def health():
    return {"status": "healthy"}
