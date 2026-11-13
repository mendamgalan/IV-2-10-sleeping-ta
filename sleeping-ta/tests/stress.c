#define _POSIX_C_SOURCE 200809L
/* Free-running stress test: students race for the TA, chairs and lock.
 * Checks the shared state after every tick. Build with -DNO_MUTEX to see
 * ThreadSanitizer report the races that the mutex prevents. */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef NO_MUTEX
static int no_lock(pthread_mutex_t *m) { (void)m; return 0; }
#define pthread_mutex_lock no_lock
#define pthread_mutex_unlock no_lock
#endif
#include "../src/engine.c"

static int check(void) {
    int seen[MAX_STUDENTS] = {0}, waiting = 0, helped = 0;
    if (waiting_count > chairs || (current < 0 && waiting_count > 0)) {
        return 0;
    }
    for (int i = 0; i < waiting_count; i++) {
        int s = queue[i];
        if (seen[s]++ || s == current || state[s] != WAITING) {
            return 0;
        }
    }
    for (int i = 0; i < n; i++) {
        waiting += state[i] == WAITING;
        helped += state[i] == GETTING_HELP;
    }
    return waiting == waiting_count && helped == (current >= 0) &&
           (current < 0 || state[current] == GETTING_HELP) &&
           arrivals == rejected + completed + waiting_count + (current >= 0);
}

int main(int argc, char **argv) {
    const int cfg[][6] = {
        {40, 3, 1, 3, 1, 4}, {40, 20, 1, 2, 5, 9}, {40, 0, 1, 1, 2, 2},
        {12, 5, 1, 9, 1, 9}, {2, 1, 1, 1, 1, 1},
    };
    int steps = argc > 1 ? atoi(argv[1]) : 3000;
    long ticks = 0;
    for (unsigned c = 0; c < sizeof cfg / sizeof cfg[0]; c++) {
        const int *k = cfg[c];
        if (sim_init(k[0], k[1], k[2], k[3], k[4], k[5], 42u + c) != 0) {
            fprintf(stderr, "sim_init failed\n");
            return 1;
        }
        sim_set_free(1);
        for (int t = 0; t < steps; t++, ticks++) {
            sim_step();
            pthread_mutex_lock(&mu);
            int ok = check();
            pthread_mutex_unlock(&mu);
            if (!ok) {
                fprintf(stderr, "invariant broken: config %u tick %d\n", c, now);
                return 1;
            }
        }
        sim_close();
    }
    printf("stress: %ld free-running ticks, invariants held\n", ticks);
    return 0;
}
