#!/usr/bin/env python3
"""Minimal MISP API mock compatible enough for PyMISP + the test playbook."""

from fastapi import FastAPI, Request

app = FastAPI(title="MISP API Mock")

MOCK_ATTRIBUTES = [
    {"type": "ip-dst", "value": "203.0.113.10", "category": "Network activity", "to_ids": True},
    {"type": "ip-dst", "value": "203.0.113.20", "category": "Network activity", "to_ids": True},
    {"type": "ip-dst", "value": "198.51.100.5", "category": "Network activity", "to_ids": True},
    {"type": "domain", "value": "malicious.example.com", "category": "Network activity", "to_ids": True},
]

_FEEDS = {
    "1": {
        "id": "1",
        "name": "firehol_level1",
        "enabled": True,
        "event_id": "1",
        "provider": "lab",
        "url": "http://misp-mock:8082/feed/firehol",
        "source_format": "misp",
    }
}


def _feed_payload(feed_id: str = "1"):
    return {"Feed": dict(_FEEDS[feed_id])}


@app.get("/servers/getVersion")
def version():
    # PyMISP parses version as int tuple — keep digits/dots only
    return {"version": "2.4.190", "pymisp_recommended_version": "2.4.190", "perm_sync": True}


@app.get("/users/view/{user_id}")
def users_view(user_id: str):
    return {
        "User": {
            "id": "1",
            "email": "admin@misp.local",
            "org_id": "1",
            "role_id": "1",
            "authkey": "lab-misp-key",
        },
        "Role": {
            "id": "1",
            "name": "admin",
            "perm_add": True,
            "perm_modify": True,
            "perm_auth": True,
            "perm_sync": True,
            "perm_admin": True,
            "perm_audit": True,
            "perm_site_admin": True,
        },
        "UserSetting": {},
        "Organisation": {"id": "1", "name": "LAB"},
    }


@app.get("/attributes/describeTypes.json")
@app.get("/attributes/describeTypes")
def describe_types():
    return {
        "result": {
            "types": ["ip-dst", "ip-src", "domain", "url", "md5", "sha256"],
            "categories": ["Network activity", "Payload delivery"],
            "category_type_mappings": {
                "Network activity": ["ip-dst", "ip-src", "domain", "url"],
                "Payload delivery": ["md5", "sha256"],
            },
            "sane_defaults": {},
        }
    }


@app.get("/feeds/index")
def feeds():
    return [_feed_payload(fid) for fid in _FEEDS]


@app.post("/feeds/loadDefaultFeeds")
def load_default_feeds():
    return {"message": "Default feed definitions added.", "url": "/feeds/index"}


@app.get("/feeds/view/{feed_id}")
def feed_view(feed_id: str):
    if feed_id not in _FEEDS:
        return {"errors": [f"Feed {feed_id} not found"]}
    return _feed_payload(feed_id)


@app.post("/feeds/edit/{feed_id}")
async def feed_edit(feed_id: str, request: Request):
    body = await request.json()
    feed = body.get("Feed", body)
    if feed_id not in _FEEDS:
        _FEEDS[feed_id] = {
            "id": str(feed_id),
            "name": feed.get("name", f"feed-{feed_id}"),
            "enabled": bool(feed.get("enabled", True)),
            "event_id": str(feed.get("event_id", "1")),
        }
    else:
        if "enabled" in feed:
            _FEEDS[feed_id]["enabled"] = bool(feed["enabled"])
        if "name" in feed and feed["name"]:
            _FEEDS[feed_id]["name"] = feed["name"]
        if "event_id" in feed and feed["event_id"]:
            _FEEDS[feed_id]["event_id"] = str(feed["event_id"])
    return _feed_payload(feed_id)


@app.get("/feeds/cacheFeeds/{feed_id}")
def cache_feed(feed_id: str):
    return {"message": f"Caching feed {feed_id}", "name": "cacheFeeds", "url": f"/feeds/view/{feed_id}"}


@app.get("/events/view/{event_id}")
def event_view(event_id: str):
    return {
        "Event": {
            "id": str(event_id),
            "info": "PySOAR lab mock event",
            "org_id": "1",
            "distribution": "0",
            "threat_level_id": "2",
            "analysis": "0",
            "Attribute": MOCK_ATTRIBUTES,
        }
    }


@app.get("/attributes/restSearch")
@app.post("/attributes/restSearch")
async def rest_search(request: Request):
    return {"response": {"Attribute": MOCK_ATTRIBUTES}}


@app.get("/health")
def health():
    return {"status": "healthy"}
