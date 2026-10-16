from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import UserContext, get_context
from app.api.schemas import ReviewIn
from app.services import anomalies as svc

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def list_alerts(ctx: UserContext = Depends(get_context),
                status: str = Query(default="all", pattern="^(all|open|reviewed|legitimate|dismissed)$")):
    items = svc.list_alerts_with_expenses(ctx.repo, ctx.prefs, status)
    counts: dict[str, int] = {}
    for a in ctx.repo.list_alerts(ctx.user_id):
        counts[a.status] = counts.get(a.status, 0) + 1
    return {"items": items, "counts": counts, "sensitivity": ctx.prefs.anomaly_sensitivity}


@router.post("/scan")
def scan(ctx: UserContext = Depends(get_context)):
    return svc.scan_all(ctx.repo, ctx.prefs)


@router.post("/{alert_id}/review")
def review(alert_id: str, body: ReviewIn, ctx: UserContext = Depends(get_context)):
    alert = svc.review_alert(ctx.repo, ctx.user_id, alert_id, body.action, body.note)
    return alert.model_dump(mode="json", exclude={"user_id"})
