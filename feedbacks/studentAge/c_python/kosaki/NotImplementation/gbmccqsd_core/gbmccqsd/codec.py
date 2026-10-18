"""[Room: room_bits][Responsibility: 2][Operation: 2]."""

from typing import Tuple

from .model import Decision, require_room_bits, require_uint


def encode_address(room: int, decision: Decision, room_bits: int = 4) -> int:
    require_room_bits(room_bits)
    require_uint(room, room_bits, "room")
    if not isinstance(decision, Decision):
        raise TypeError("decision must be a Decision")
    return (room << 4) | decision.nibble


def decode_address(value: int, room_bits: int = 4) -> Tuple[int, Decision]:
    require_room_bits(room_bits)
    require_uint(value, room_bits + 4, "address")
    return value >> 4, Decision.from_nibble(value & 0xF)
