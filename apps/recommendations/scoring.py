"""
Transparent, deterministic candidate scoring engine for technician allocation (Phase 10).
Uses explainable weighted distance, workload, and skill matching.
Strictly prohibits non-deterministic or unexplainable black-box algorithms.
"""

from typing import Dict, Any, List, Optional


def calculate_technician_score(
    distance_km: float,
    active_tasks: int,
    has_matching_skill: bool = True,
    is_available: bool = True,
    hourly_labor_rate: Optional[float] = None,
    sla_urgency_factor: float = 1.0,
    weight_dist: float = 0.4,
    weight_workload: float = 0.4,
    weight_skill: float = 0.2,
) -> Dict[str, Any]:
    """
    Computes a transparent, deterministic 0-100 score for a technician candidate.

    Formula:
    Score = w_dist * S_dist + w_workload * S_workload + w_skill * S_skill (gated by is_available)

    Where:
    - S_dist = max(0, 100 - distance_km * 10)
    - S_workload = max(0, 100 - active_tasks * 20)
    - S_skill = 100 if has_matching_skill else 50
    - S_avail = 100 if is_available else 0 (unavailable technician receives score 0.0)
    """
    if not is_available:
        return {
            "score": 0.0,
            "subscores": {
                "distance_score": round(max(0.0, 100.0 - float(distance_km) * 10.0), 1),
                "workload_score": round(max(0.0, 100.0 - float(active_tasks) * 20.0), 1),
                "skill_score": 100.0 if has_matching_skill else 50.0,
                "availability_score": 0.0,
            },
            "weights": {
                "distance": weight_dist,
                "workload": weight_workload,
                "skill": weight_skill,
            },
            "hourly_labor_rate": float(hourly_labor_rate) if hourly_labor_rate is not None else None,
            "sla_urgency_factor": sla_urgency_factor,
            "formula": "Score = 0.0 (Gated: Technician unavailable)"
        }

    s_dist = max(0.0, 100.0 - float(distance_km) * 10.0)
    s_workload = max(0.0, 100.0 - float(active_tasks) * 20.0)
    s_skill = 100.0 if has_matching_skill else 50.0

    total_score = (
        float(weight_dist) * s_dist +
        float(weight_workload) * s_workload +
        float(weight_skill) * s_skill
    )
    total_score = round(min(100.0, max(0.0, total_score)), 2)

    subscores = {
        "distance_score": round(s_dist, 1),
        "workload_score": round(s_workload, 1),
        "skill_score": round(s_skill, 1),
        "availability_score": 100.0,
    }
    if hourly_labor_rate is not None:
        subscores["hourly_labor_rate"] = float(hourly_labor_rate)

    return {
        "score": total_score,
        "subscores": subscores,
        "weights": {
            "distance": weight_dist,
            "workload": weight_workload,
            "skill": weight_skill,
        },
        "hourly_labor_rate": float(hourly_labor_rate) if hourly_labor_rate is not None else None,
        "sla_urgency_factor": sla_urgency_factor,
        "formula": "Score = 0.4*max(0, 100 - dist*10) + 0.4*max(0, 100 - tasks*20) + 0.2*(100 if skill else 50)"
    }

