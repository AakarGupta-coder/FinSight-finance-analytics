"""Savings goals and the What-If simulator."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.api.deps import UserContext, get_context
from app.api.schemas import ContributionIn, GoalIn, GoalUpdateIn, RequiredReductionIn, SimulationIn
from app.domain.dates import today_in
from app.services import goals as goal_svc
from app.services import simulator

goals_router = APIRouter(prefix="/goals", tags=["goals"])
simulations_router = APIRouter(prefix="/simulations", tags=["simulations"])


def _out(ctx: UserContext, goal) -> dict:
    data = goal_svc.serialize_goal(goal, today_in(ctx.prefs.timezone))
    data.pop("user_id", None)
    return data


@goals_router.get("")
def list_goals(ctx: UserContext = Depends(get_context)):
    today = today_in(ctx.prefs.timezone)
    goals = [goal_svc.serialize_goal(g, today) for g in ctx.repo.list_goals(ctx.user_id)]
    for g in goals:
        g.pop("user_id", None)
    goals.sort(key=lambda g: (g["archived"], g["completed"], g["target_date"] or "9999"))
    active = [g for g in goals if not g["archived"]]
    return {
        "items": goals,
        "summary": {
            "total_target_minor": sum(g["target_minor"] for g in active),
            "total_saved_minor": sum(min(g["saved_minor"], g["target_minor"]) for g in active),
            "required_monthly_minor": sum(g["required_monthly_minor"] or 0 for g in active),
            "active_count": sum(1 for g in active if not g["completed"]),
            "completed_count": sum(1 for g in active if g["completed"]),
        },
    }


@goals_router.post("", status_code=201)
def create_goal(body: GoalIn, ctx: UserContext = Depends(get_context)):
    goal = goal_svc.create_goal(ctx.repo, ctx.prefs, body.name, body.target_minor, body.saved_minor, body.target_date)
    return _out(ctx, goal)


@goals_router.get("/{goal_id}")
def get_goal(goal_id: str, ctx: UserContext = Depends(get_context)):
    return _out(ctx, goal_svc.get_goal(ctx.repo, ctx.user_id, goal_id))


@goals_router.put("/{goal_id}")
def update_goal(goal_id: str, body: GoalUpdateIn, ctx: UserContext = Depends(get_context)):
    goal = goal_svc.update_goal(ctx.repo, ctx.prefs, goal_id, name=body.name, target_minor=body.target_minor,
                                target_date=body.target_date, clear_target_date=body.clear_target_date,
                                archived=body.archived)
    return _out(ctx, goal)


@goals_router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, ctx: UserContext = Depends(get_context)):
    goal_svc.delete_goal(ctx.repo, ctx.user_id, goal_id)
    return Response(status_code=204)


@goals_router.post("/{goal_id}/contributions", status_code=201)
def add_contribution(goal_id: str, body: ContributionIn, ctx: UserContext = Depends(get_context)):
    goal = goal_svc.add_contribution(ctx.repo, ctx.prefs, goal_id, body.amount_minor, body.date, body.note)
    return _out(ctx, goal)


@goals_router.delete("/{goal_id}/contributions/{contribution_id}")
def delete_contribution(goal_id: str, contribution_id: str, ctx: UserContext = Depends(get_context)):
    return _out(ctx, goal_svc.delete_contribution(ctx.repo, ctx.prefs, goal_id, contribution_id))


@simulations_router.post("")
def simulate(body: SimulationIn, ctx: UserContext = Depends(get_context)):
    scenarios = [
        simulator.Scenario(name=s.name, adjustments=[simulator.Adjustment(a.category, a.mode, a.value)
                                                     for a in s.adjustments])
        for s in body.scenarios
    ]
    return simulator.run_scenarios(ctx.repo, ctx.prefs, scenarios, body.baseline, body.goal_id)


@simulations_router.post("/required-savings")
def required_savings(body: RequiredReductionIn, ctx: UserContext = Depends(get_context)):
    return simulator.required_reduction(ctx.repo, ctx.prefs, goal_id=body.goal_id, target_minor=body.target_minor,
                                        months=body.months, baseline_mode=body.baseline)
