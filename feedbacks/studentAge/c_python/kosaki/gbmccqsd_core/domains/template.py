"""Working neutral template: decisions are supplied explicitly by the caller.

Room graph and payloads below are examples, not definitions of the theory.
Copy this file to implement a new domain. No core edits are needed.
"""

from typing import Any, Mapping, Optional

from gbmccqsd import (
    Decision, Observation, OperationResult, Route, State, Transition,
)


class TemplateDomain:
    def __init__(self, next_rooms: Optional[Mapping[Route, int]] = None) -> None:
        # An example graph, shared across source rooms; replace as needed.
        self.next_rooms = dict(next_rooms) if next_rooms is not None else {
            Route.STRAIGHT: 1, Route.JAB: 2, Route.TWIST: 3,
        }

    def observe(self, state: State, event: Any, timestamp: float,
                previous_feedback: Any) -> Observation:
        return Observation(timestamp, {
            "event": event,
            "previous_feedback": previous_feedback,
        })

    def choose(self, state: State, observation: Observation) -> Decision:
        event = observation.data["event"]
        return Decision(event["responsibility"], event["operation"])

    def operate(self, state: State, observation: Observation,
                decision: Decision) -> OperationResult:
        # Replace with actual domain logic (Phi). SET subtypes such as
        # stop/place/contact can be distinguished in the event payload.
        return OperationResult({
            "operation": decision.operation.name,
            "payload": observation.data["event"].get("payload"),
        })

    def transition(self, state: State, observation: Observation,
                   decision: Decision, result: OperationResult,
                   route: Route) -> Transition:
        # Example Gamma: Observe stays; other modes use configured targets.
        # O/S/J/T classify a route; core does not prescribe room destinations.
        next_room = self.next_rooms.get(route, state.room)
        data = dict(state.data)
        data["steps"] = data.get("steps", 0) + 1
        data["last_output"] = result.value
        return Transition(next_room, data, {
            "previous_route": route.value,
            "previous_output": result.value,
        })
