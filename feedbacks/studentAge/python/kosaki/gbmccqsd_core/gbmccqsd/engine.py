"""Execute one observation -> decision -> Phi -> D -> Gamma cycle."""

from copy import deepcopy
from math import isfinite
from typing import Any, Callable, Optional

from .codec import encode_address
from .model import (
    Decision, Domain, Observation, OperationResult, Route, State,
    StepRecord, Transition, require_room_bits, require_uint,
)
from .router import route_decision


class Engine:
    def __init__(self, domain: Domain, initial_state: State,
                 room_bits: int = 4,
                 router: Callable[[Decision], Route] = route_decision) -> None:
        require_room_bits(room_bits)
        require_uint(initial_state.room, room_bits, "initial room")
        self.domain = domain
        self.room_bits = room_bits
        self.router = router
        self._state = deepcopy(initial_state)
        self._feedback: Any = None
        self._last_timestamp: Optional[float] = None
        self._step_count = 0
        self._last_record: Optional[StepRecord] = None
        self._busy = False

    @property
    def state(self) -> State:
        return deepcopy(self._state)

    @property
    def last_record(self) -> Optional[StepRecord]:
        return deepcopy(self._last_record)

    @property
    def step_count(self) -> int:
        return self._step_count

    def step(self, event: Any, *, timestamp: float) -> StepRecord:
        """Timestamp is caller supplied, finite and nondecreasing (equal allowed).

        State is committed only after all hooks and validation succeed.
        Hooks receive copies; external I/O and domain-object mutations cannot
        be rolled back. Data/event/result must support deepcopy.
        Engine instances are synchronous and must not be shared across threads.
        """
        if self._busy:
            raise RuntimeError("reentrant step is not supported")
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise ValueError("timestamp must be a finite number")
        try:
            time = float(timestamp)
        except OverflowError as exc:
            raise ValueError("timestamp must be a finite number") from exc
        if not isfinite(time):
            raise ValueError("timestamp must be finite")
        if self._last_timestamp is not None and time < self._last_timestamp:
            raise ValueError("timestamp must not go backwards")

        self._busy = True
        try:
            before = deepcopy(self._state)
            observed = self.domain.observe(deepcopy(before), deepcopy(event), time,
                                           deepcopy(self._feedback))
            if not isinstance(observed, Observation):
                raise TypeError("observe must return Observation")
            if (isinstance(observed.timestamp, bool)
                    or not isinstance(observed.timestamp, (int, float))
                    or observed.timestamp != time):
                raise ValueError("observe must preserve the supplied timestamp")
            observed = deepcopy(observed)
            decision = self.domain.choose(deepcopy(before), deepcopy(observed))
            if not isinstance(decision, Decision):
                raise TypeError("choose must return Decision")
            result = self.domain.operate(deepcopy(before), deepcopy(observed), decision)
            if not isinstance(result, OperationResult):
                raise TypeError("operate must return OperationResult")
            result = deepcopy(result)
            mode = self.router(decision)
            if not isinstance(mode, Route):
                raise TypeError("router must return Route")
            transition = self.domain.transition(
                deepcopy(before), deepcopy(observed), decision, deepcopy(result), mode)
            if not isinstance(transition, Transition):
                raise TypeError("transition must return Transition")
            require_uint(transition.next_room, self.room_bits, "next room")
            after = State(transition.next_room, deepcopy(transition.data))
            feedback = deepcopy(transition.feedback)
            record = StepRecord(
                self._step_count, before, observed, decision,
                encode_address(before.room, decision, self.room_bits),
                result, mode, after, feedback,
            )
            # Prepare all copies before commit, including the returned record.
            next_state = deepcopy(after)
            next_feedback = deepcopy(feedback)
            stored_record = deepcopy(record)
            returned_record = deepcopy(record)
            self._state = next_state
            self._feedback = next_feedback
            self._last_timestamp = time
            self._step_count += 1
            self._last_record = stored_record
            return returned_record
        finally:
            self._busy = False
