"""Run from the project root: python -m examples.basic"""

from domains.template import TemplateDomain
from gbmccqsd import Engine, State


def main() -> None:
    engine = Engine(TemplateDomain(), State(room=0))
    # Demonstrate every combination of responsibility and operation.
    for nibble in range(16):
        record = engine.step({
            "responsibility": nibble >> 2,
            "operation": nibble & 3,
            "payload": "example {}".format(nibble),
        }, timestamp=nibble * 0.03)
        print("t={:.2f}  addr=0x{:02X}  control={:04b}  {:8s}  room {} -> {}".format(
            record.observation.timestamp, record.address, record.decision.nibble,
            record.route.value, record.before.room, record.after.room))


if __name__ == "__main__":
    main()
