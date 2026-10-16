#include <stdio.h>
#include <stdint.h>

static uint8_t step(uint8_t state, uint8_t input) {
    uint8_t room = (state >> 1) & 15u;
    uint8_t back = (state >> 6) & 3u;
    uint8_t next_room = (room + 1u + input) & 15u;
    uint8_t next_back = ((back << 1) | input) & 3u;
    uint8_t output = ((next_room == 4u || next_room == 8u ||
                       next_room == 12u || next_room == 15u) && next_back == 3u) ? 1u : 0u;
    return (uint8_t)((next_back << 6) | (output << 5) | (next_room << 1) | input);
}

int main(int argc, char **argv) {
    const char *data = argc > 1 ? argv[1] : "101100101011";
    uint8_t state = 0;
    int t;
    if (!*data) { fprintf(stderr, "Input must be binary.\n"); return 1; }
    for (t = 0; data[t]; ++t) {
        if (data[t] != '0' && data[t] != '1') {
            fprintf(stderr, "Input must be binary.\n"); return 1;
        }
    }
    puts("t input back room output state");
    for (t = 0; data[t]; ++t) {
        state = step(state, (uint8_t)(data[t] - '0'));
        printf("%2d   %c     %u    %X     %u    %02X\n", t, data[t],
               (unsigned)((state >> 6) & 3u), (unsigned)((state >> 1) & 15u),
               (unsigned)((state >> 5) & 1u), (unsigned)state);
    }
    return 0;
}
