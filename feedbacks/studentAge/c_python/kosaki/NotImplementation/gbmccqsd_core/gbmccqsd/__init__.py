"""Domain-independent Room / Responsibility / Operation transition core."""

from .codec import decode_address, encode_address
from .engine import Engine
from .model import (
    Decision, Domain, Observation, Operation, OperationResult,
    Route, State, StepRecord, Transition,
)
from .router import route_decision

__all__ = [
    "Decision", "Domain", "Engine", "Observation", "Operation",
    "OperationResult", "Route", "State", "StepRecord", "Transition",
    "decode_address", "encode_address", "route_decision",
]
