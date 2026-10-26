#define _POSIX_C_SOURCE 200809L
/* Exercise partial initialization cleanup without exhausting host resources. */
#include <pthread.h>
#include <semaphore.h>
#include <errno.h>
#include <assert.h>
static int thread_calls, sem_calls, fail_thread, fail_sem;
static int injected_create(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
static int injected_sem_init(sem_t *, int, unsigned);
#define pthread_create injected_create
#define sem_init injected_sem_init
#include "../src/engine.c"
#undef pthread_create
#undef sem_init

static int injected_create(pthread_t *t, const pthread_attr_t *attr,
                           void *(*fn)(void *), void *arg) {
    if (++thread_calls == fail_thread) {
        return EAGAIN;
    }
    return pthread_create(t, attr, fn, arg);
}
static int injected_sem_init(sem_t *sem, int shared, unsigned value) {
    if (++sem_calls == fail_sem) {
        errno = ENOSPC;
        return -1;
    }
    return sem_init(sem, shared, value);
}
int main(void) {
    for (int which = 0; which < 3; which++) {
        thread_calls = sem_calls = 0;
        fail_thread = which == 0 ? 1 : which == 1 ? 4 : 0;
        fail_sem = which == 2 ? 6 : 0;
        assert(sim_init(8, 3, 1, 2, 1, 2, 42) == -3);
        fail_thread = fail_sem = 0;
        assert(sim_init(8, 3, 1, 2, 1, 2, 42) == 0);
        for (int i = 0; i < 10; i++) {
            sim_step();
        }
        sim_close();
        sim_close();
    }
    return 0;
}
