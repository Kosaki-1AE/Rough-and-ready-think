"""Illustrative manual annotations, not inferred dancer intent.

Here responsibility codes 0..3 are explicitly assigned by this example.
No universal meaning for responsibility codes is defined by the core.
Run: python -m examples.dance
"""

from typing import Any

from domains.template import TemplateDomain
from gbmccqsd import Engine, State


class DanceDomain(TemplateDomain):
    # Example room names; room IDs/destinations are an application choice.
    ROOMS = {0: "場を観測", 1: "継続", 2: "未回収を保持", 3: "解釈を更新"}

    def observe(self, state: State, event: Any, timestamp: float,
                previous_feedback: Any):
        # A real application could preprocess pose/music here.
        # This example accepts manually annotated observation and action.
        return super().observe(state, event, timestamp, previous_feedback)


def main() -> None:
    engine = Engine(DanceDomain(), State(room=0))
    # Sample code meanings only: 00/01 original focus, 10/11 reinterpret/delegate.
    events = [
        (0.00, 0, 0, "キックを観測し、胸のhitを記述"),       # Observe
        (0.25, 0, 3, "音への当て方を維持する"),               # Straight
        (0.50, 2, 0, "未回収の間を残す"),                     # Jab
        (0.75, 2, 2, "反動をwaveへ読み替える"),                # Twist
    ]
    for time, responsibility, operation, description in events:
        record = engine.step({
            "responsibility": responsibility,
            "operation": operation,
            "payload": description,
        }, timestamp=time)
        print("{:.2f}s | {} | {} -> {} | {}".format(
            time, record.route.value, DanceDomain.ROOMS[record.before.room],
            DanceDomain.ROOMS[record.after.room], description))


if __name__ == "__main__":
    main()
