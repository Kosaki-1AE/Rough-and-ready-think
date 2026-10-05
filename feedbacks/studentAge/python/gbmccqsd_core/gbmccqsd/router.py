"""D: classify the control nibble using the source's final 2x2 rule."""

from .model import Decision, Route


def route_decision(decision: Decision) -> Route:
    # b3 = responsibility high bit; b1 = operation high bit.
    quadrant = ((decision.responsibility >> 1) << 1) | (int(decision.operation) >> 1)
    return (Route.OBSERVE, Route.STRAIGHT, Route.JAB, Route.TWIST)[quadrant]
