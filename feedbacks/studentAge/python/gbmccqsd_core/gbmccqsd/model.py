"""Common data types. Domain-specific meanings belong outside this module."""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Mapping, Optional, Protocol


def require_uint(value: int, bits: int, name: str) -> None:
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise ValueError("{} must be an integer in 0..{}".format(name, (1 << bits) - 1))


def require_room_bits(bits: int) -> None:
    if type(bits) is not int or bits not in (2, 3, 4):
        raise ValueError("room_bits must be 2, 3, or 4")


class Operation(IntEnum):
    HIT = 0       # 打つ / 00 / 1
    SHOOT = 1     # 弾く / 01 / i
    OFF = 2       # 外す / 10 / -1
    SET = 3       # 置く / 11 / -i（止める・当てるも同じ分類）

    @property
    def complex_unit(self) -> complex:
        """Symbolic correspondence only; this does not prescribe dynamics."""
        return (1 + 0j, 1j, -1 + 0j, -1j)[int(self)]


class Route(str, Enum):
    OBSERVE = "Observe"
    STRAIGHT = "Straight"
    JAB = "Jab"
    TWIST = "Twist"


@dataclass(frozen=True)
class Decision:
    responsibility: int
    operation: Operation

    def __post_init__(self) -> None:
        require_uint(self.responsibility, 2, "responsibility")
        if not isinstance(self.operation, Operation):
            require_uint(self.operation, 2, "operation")
            object.__setattr__(self, "operation", Operation(self.operation))

    @property
    def nibble(self) -> int:
        return (self.responsibility << 2) | int(self.operation)

    @classmethod
    def from_nibble(cls, value: int) -> "Decision":
        require_uint(value, 4, "decision nibble")
        return cls(value >> 2, Operation(value & 0b11))


@dataclass(frozen=True)
class State:
    room: int
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    timestamp: float
    data: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationResult:
    value: Any = None
    # Optional separate 4-bit result, whose meanings the domain must define.
    result_code: Optional[int] = None

    def __post_init__(self) -> None:
        if self.result_code is not None:
            require_uint(self.result_code, 4, "result_code")


@dataclass(frozen=True)
class Transition:
    next_room: int
    data: Mapping[str, Any] = field(default_factory=dict)
    feedback: Any = None


@dataclass(frozen=True)
class StepRecord:
    index: int
    before: State
    observation: Observation
    decision: Decision
    address: int
    result: OperationResult
    route: Route
    after: State
    feedback: Any


class Domain(Protocol):
    """Implement these four methods in a separate domain file."""

    def observe(self, state: State, event: Any, timestamp: float,
                previous_feedback: Any) -> Observation:
        ...

    def choose(self, state: State, observation: Observation) -> Decision:
        ...

    def operate(self, state: State, observation: Observation,
                decision: Decision) -> OperationResult:
        """Phi: execute/describe the local operation."""
        ...

    def transition(self, state: State, observation: Observation,
                   decision: Decision, result: OperationResult,
                   route: Route) -> Transition:
        """Gamma: choose the next room, data, and feedback."""
        ...
