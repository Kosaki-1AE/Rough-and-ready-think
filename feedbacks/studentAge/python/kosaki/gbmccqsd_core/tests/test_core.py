import unittest

from domains.template import TemplateDomain
from gbmccqsd import (
    Decision, Engine, Observation, Operation, OperationResult, Route,
    State, Transition, decode_address, encode_address, route_decision,
)


class CoreTests(unittest.TestCase):
    def test_all_sixteen_routes_against_source_table(self):
        # Explicit expected sets from the source, independent of router math.
        groups = {
            Route.OBSERVE: (0x0, 0x1, 0x4, 0x5),
            Route.STRAIGHT: (0x2, 0x3, 0x6, 0x7),
            Route.JAB: (0x8, 0x9, 0xC, 0xD),
            Route.TWIST: (0xA, 0xB, 0xE, 0xF),
        }
        for mode, nibbles in groups.items():
            for nibble in nibbles:
                with self.subTest(nibble=nibble):
                    self.assertEqual(route_decision(Decision.from_nibble(nibble)), mode)

    def test_address_roundtrip_every_valid_address(self):
        for bits in (2, 3, 4):
            for address in range(1 << (bits + 4)):
                room, decision = decode_address(address, bits)
                self.assertEqual(encode_address(room, decision, bits), address)
        self.assertEqual(encode_address(0xA, Decision(2, Operation.OFF)), 0xAA)

    def test_reject_invalid_codes(self):
        for value in (-1, 4, True, 1.5, "1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Decision(value, Operation.HIT)
                with self.assertRaises(ValueError):
                    Decision(0, value)
        for bits in (0, 1, 5, True, 4.0):
            with self.assertRaises(ValueError):
                encode_address(0, Decision(0, 0), bits)
        with self.assertRaises(ValueError):
            encode_address(16, Decision(0, 0))
        with self.assertRaises(ValueError):
            decode_address(256)
        with self.assertRaises(ValueError):
            Decision.from_nibble(16)
        with self.assertRaises(ValueError):
            OperationResult(result_code=16)
        self.assertEqual(OperationResult(result_code=15).result_code, 15)

    def test_sequence_feedback_and_mode_observe(self):
        engine = Engine(TemplateDomain(), State(0))
        first = engine.step({"responsibility": 0, "operation": 0}, timestamp=0)
        self.assertEqual(first.route, Route.OBSERVE)
        self.assertEqual(first.after.room, 0)
        second = engine.step({"responsibility": 2, "operation": 2}, timestamp=0.03)
        self.assertEqual(second.route, Route.TWIST)
        self.assertEqual(second.after.room, 3)
        self.assertEqual(second.observation.data["previous_feedback"], first.feedback)
        self.assertEqual(second.after.data["steps"], 2)
        self.assertEqual(engine.step_count, 2)

    def test_timestamp_validation_and_equal_timestamps(self):
        engine = Engine(TemplateDomain(), State(0))
        event = {"responsibility": 0, "operation": 0}
        engine.step(event, timestamp=1)
        engine.step(event, timestamp=1)
        for time in (0.9, float("nan"), float("inf"), True, "2", 10 ** 1000):
            with self.subTest(time_type=type(time).__name__):
                with self.assertRaises(ValueError):
                    engine.step(event, timestamp=time)
        self.assertEqual(engine.step_count, 2)

    def test_bad_next_room_preserves_state_feedback_and_time(self):
        domain = TemplateDomain({Route.STRAIGHT: 16})
        engine = Engine(domain, State(0, {"nested": {"value": 1}}))
        event = {"responsibility": 0, "operation": 2}
        with self.assertRaises(ValueError):
            engine.step(event, timestamp=10)
        self.assertEqual(engine.state, State(0, {"nested": {"value": 1}}))
        self.assertIsNone(engine.last_record)
        self.assertEqual(engine.step_count, 0)
        domain.next_rooms[Route.STRAIGHT] = 1
        record = engine.step(event, timestamp=1)
        self.assertIsNone(record.observation.data["previous_feedback"])

    def test_callback_mutation_does_not_leak_on_failure(self):
        class FailingDomain(TemplateDomain):
            def operate(self, state, observation, decision):
                state.data["nested"]["value"] = 99
                raise RuntimeError("example failure")
        engine = Engine(FailingDomain(), State(0, {"nested": {"value": 1}}))
        with self.assertRaises(RuntimeError):
            engine.step({"responsibility": 0, "operation": 0}, timestamp=0)
        self.assertEqual(engine.state.data["nested"]["value"], 1)
        self.assertEqual(engine.step_count, 0)

    def test_records_and_state_are_separate_snapshots(self):
        event = {"responsibility": 0, "operation": 0, "payload": {"x": [1]}}
        initial = State(0, {"nested": {"x": 1}})
        engine = Engine(TemplateDomain(), initial)
        initial.data["nested"]["x"] = 9
        record = engine.step(event, timestamp=0)
        event["payload"]["x"].append(2)
        record.after.data["last_output"]["payload"]["x"].append(3)
        engine.state.data["nested"]["x"] = 8
        self.assertEqual(engine.state.data["nested"]["x"], 1)
        self.assertEqual(engine.state.data["last_output"]["payload"]["x"], [1])
        self.assertEqual(engine.last_record.after.data["last_output"]["payload"]["x"], [1])

    def test_router_can_be_replaced(self):
        engine = Engine(TemplateDomain(), State(0), router=lambda decision: Route.JAB)
        record = engine.step({"responsibility": 0, "operation": 0}, timestamp=0)
        self.assertEqual(record.route, Route.JAB)
        self.assertEqual(record.after.room, 2)

    def test_observation_must_preserve_timestamp(self):
        class BadDomain(TemplateDomain):
            def observe(self, state, event, timestamp, previous_feedback):
                return Observation(timestamp + 1, {"event": event})
        engine = Engine(BadDomain(), State(0))
        with self.assertRaises(ValueError):
            engine.step({"responsibility": 0, "operation": 0}, timestamp=0)
        self.assertEqual(engine.step_count, 0)

    def test_result_code_is_independent_of_routing(self):
        class ResultDomain(TemplateDomain):
            def operate(self, state, observation, decision):
                return OperationResult("domain result", result_code=15)
        engine = Engine(ResultDomain(), State(0))
        record = engine.step({"responsibility": 0, "operation": 2}, timestamp=0)
        self.assertEqual(record.route, Route.STRAIGHT)
        self.assertEqual(record.result.result_code, 15)


if __name__ == "__main__":
    unittest.main()
