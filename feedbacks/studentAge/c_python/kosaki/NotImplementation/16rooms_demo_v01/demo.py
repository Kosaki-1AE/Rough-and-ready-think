# Python 3.6+ / standard library only
# 8-bit state: BB O RRRR I
import sys

def step(state, inp):
    room = (state >> 1) & 15
    back = (state >> 6) & 3
    # Toy policy: input 1 advances two rooms, input 0 advances one.
    # Backroom bits track the last two binary inputs (not full history).
    next_room = (room + 1 + inp) & 15
    next_back = ((back << 1) | inp) & 3
    out = 1 if (next_room in (4, 8, 12, 15) and next_back == 3) else 0
    return (next_back << 6) | (out << 5) | (next_room << 1) | inp

def main():
    state = 0
    data = sys.argv[1] if len(sys.argv) > 1 else '101100101011'
    if not data or any(c not in '01' for c in data):
        print('usage: python demo.py [binary_input_sequence]')
        return 1
    print('t input back room output state')
    for t, ch in enumerate(data):
        state = step(state, int(ch))
        print('%2d   %s     %d    %X     %d    %02X' % (t, ch, (state >> 6) & 3, (state >> 1) & 15, (state >> 5) & 1, state))
    return 0

if __name__ == '__main__':
    sys.exit(main())
