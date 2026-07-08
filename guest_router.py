"""FastAPI router for guest access and admin management."""

from __future__ import annotations

import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

from guest_store import (
    create_guest,
    verify_token,
    consume_token,
    list_guests,
    toggle_guest,
    adjust_quota,
    get_analytics,
)
from visit_store import record_visit, get_visit_stats

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "rwe-admin-2024")

guest_router = APIRouter()
admin_router = APIRouter()


# ── Guest endpoints ──────────────────────────────────────────────────────────

@guest_router.get("/guest/verify/{token}")
def verify(token: str):
    ok, reason, guest = verify_token(token)
    if not ok:
        raise HTTPException(status_code=403, detail=reason)
    return {
        "name": guest["name"],
        "quota": guest["quota"],
        "used": guest["used"],
        "remaining": guest["quota"] - guest["used"],
        "expires": guest["expires"],
    }


class TrackVisitRequest(BaseModel):
    path: str


@guest_router.post("/track-visit")
def track_visit(req: TrackVisitRequest):
    record_visit(req.path[:200])
    return {"ok": True}


# ── Admin endpoints ──────────────────────────────────────────────────────────

def _check_admin(secret: Optional[str]):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


class CreateGuestRequest(BaseModel):
    name: str
    email: str = ""
    quota: int = 10
    days_valid: int = 30
    note: str = ""


@admin_router.post("/admin/guest")
def admin_create_guest(req: CreateGuestRequest, x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    guest = create_guest(
        name=req.name,
        email=req.email,
        quota=req.quota,
        days_valid=req.days_valid,
        note=req.note,
    )
    return guest


@admin_router.get("/admin/guests")
def admin_list_guests(x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    return list_guests()


@admin_router.patch("/admin/guest/{token}")
def admin_toggle_guest(token: str, active: bool, x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    ok = toggle_guest(token, active)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"ok": True}


@admin_router.patch("/admin/guest/{token}/quota")
def admin_adjust_quota(token: str, delta: int, x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    guest = adjust_quota(token, delta)
    if not guest:
        raise HTTPException(status_code=404, detail="Token not found")
    return guest


@admin_router.get("/admin/analytics")
def admin_analytics(x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    return get_analytics()


@admin_router.get("/admin/visit-stats")
def admin_visit_stats(x_admin_secret: Optional[str] = Header(None)):
    _check_admin(x_admin_secret)
    return get_visit_stats()
