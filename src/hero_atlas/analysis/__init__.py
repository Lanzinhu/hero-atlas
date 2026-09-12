"""Analise: envelope, energia, trim, estabilidade, requisitos."""

from .energy import (
    TurbineEndurance,
    disk_area_from_rotors_m2,
    electric_endurance_s,
    electrical_hover_power_W,
    power_per_newton_W_N,
    turbine_endurance_s,
)
from .envelope import (
    InstallationLosses,
    MassBudget,
    MassClosureResult,
    ThrustEnvelope,
    mass_closure,
    solve_envelope,
    thrust_effective_available_N,
    thrust_effective_required_N,
)
from .requirements import ActuatorRequirement, AdmissibleRegion, Relation
from .trim import CaptureAssessment, TrimSolution, TrimTarget, assess_capture, solve_trim

__all__ = [
    "ActuatorRequirement",
    "AdmissibleRegion",
    "CaptureAssessment",
    "TrimSolution",
    "TrimTarget",
    "assess_capture",
    "solve_trim",
    "InstallationLosses",
    "MassBudget",
    "MassClosureResult",
    "Relation",
    "ThrustEnvelope",
    "TurbineEndurance",
    "disk_area_from_rotors_m2",
    "electric_endurance_s",
    "electrical_hover_power_W",
    "mass_closure",
    "power_per_newton_W_N",
    "solve_envelope",
    "thrust_effective_available_N",
    "thrust_effective_required_N",
    "turbine_endurance_s",
]
