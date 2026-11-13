#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_STUDENTS 40
#define MAX_CHAIRS 20
#define RECENT_EVENTS 6
#define EVENT_LENGTH 128

enum StudentState { PROGRAMMING, WAITING, GETTING_HELP };
enum Arrival { KEEP_PROGRAMMING, WAKE_TA, TAKE_CHAIR };

/* Public functions have one caller (the UI/controller thread).
 * Workers access the shared model only while holding mu.
 *
 *   work       an arriving student wakes the sleeping TA
 *   started    the TA tells that student that help has started
 *   called[i]  student i sits on a chair until the TA calls it
 *   done[i]    student i is helped until the TA finishes
 *   returned   student i tells the TA that it is programming again
 *   ticks[i], ta_tick, ack   model clock handshake with the controller */
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static sem_t work, ta_tick, ack, started, returned;
static sem_t ticks[MAX_STUDENTS], called[MAX_STUDENTS], done[MAX_STUDENTS];
static pthread_t ta, students[MAX_STUDENTS];
static int n, chairs, arrival_min, arrival_max, help_min, help_max;
static int active, stopping, now, current = -1, queue[MAX_STUDENTS];
static int waiting_count, remaining, state[MAX_STUDENTS], due[MAX_STUDENTS];
static int visits[MAX_STUDENTS], joined[MAX_STUDENTS];
static int rejected, completed, arrivals, busy, wait_sum;
static uint32_t rng, order_rng;
static int common_sems, tick_sems, called_sems, done_sems;
static int ta_created, students_created;

/* Full history lives in a temporary file, not a fixed-size memory buffer.
 * The UI reads only this small ring; exporting streams the complete file. */
static FILE *journal;
static char recent[RECENT_EVENTS][EVENT_LENGTH];
static unsigned recent_count, recent_next;
static int journal_error;
static char *history;
static size_t history_capacity;

static void wait_sem(sem_t *sem) {
    int result;
    do {
        result = sem_wait(sem);
    } while (result < 0 && errno == EINTR);
    /* A non-EINTR failure means an invalid synchronization object. */
    if (result < 0) {
        perror("sem_wait");
        abort();
    }
}

/* LCG low bits repeat with a short period, so use the high bits. */
static int random_between(int low, int high) {
    rng = rng * 1664525u + 1013904223u;
    return low + (int)((rng >> 16) % (unsigned)(high - low + 1));
}

static int random_index(int bound) {
    order_rng = order_rng * 1664525u + 1013904223u;
    return (int)((order_rng >> 16) % (unsigned)bound);
}

static void record_event(const char *kind, int id) {
    char *line = recent[recent_next];
    snprintf(line, EVENT_LENGTH, "%d,%s,%d,%d\n",
             now, kind, id + 1, waiting_count);
    recent_next = (recent_next + 1) % RECENT_EVENTS;
    if (recent_count < RECENT_EVENTS) {
        recent_count++;
    }
    if (!journal_error && fputs(line, journal) == EOF) {
        journal_error = 1;
    }
}

static void begin_help(int id) {
    current = id;
    state[id] = GETTING_HELP;
    remaining = random_between(help_min, help_max);
    wait_sum += now - joined[id];
    record_event("help_start", id);
}

static int is_stopping(void) {
    pthread_mutex_lock(&mu);
    int result = stopping;
    pthread_mutex_unlock(&mu);
    return result;
}

static void *teacher(void *unused) {
    (void)unused;
    for (;;) {
        wait_sem(&work); /* No student: the TA really sleeps here. */
        pthread_mutex_lock(&mu);
        if (stopping) {
            pthread_mutex_unlock(&mu);
            break;
        }
        begin_help(current);
        pthread_mutex_unlock(&mu);
        sem_post(&started);

        for (;;) {
            wait_sem(&ta_tick);
            pthread_mutex_lock(&mu);
            if (stopping) {
                pthread_mutex_unlock(&mu);
                return NULL;
            }
            busy++;
            remaining--;
            int finished = -1;
            if (remaining == 0) {
                finished = current;
                completed++;
                visits[finished]++;
                record_event("help_end", finished);
            }
            pthread_mutex_unlock(&mu);

            int next = -1;
            if (finished >= 0) {
                sem_post(&done[finished]);
                wait_sem(&returned);
                pthread_mutex_lock(&mu);
                if (waiting_count > 0) {
                    next = queue[0];
                    waiting_count--;
                    memmove(queue, queue + 1,
                            (size_t)waiting_count * sizeof(queue[0]));
                    begin_help(next);
                } else {
                    current = -1;
                    record_event("sleep", -1);
                }
                pthread_mutex_unlock(&mu);
                if (next >= 0) {
                    sem_post(&called[next]); /* call the first student in line */
                }
            }
            sem_post(&ack);
            if (finished >= 0 && next < 0) {
                break; /* queue empty: go back to sleep */
            }
        }
    }
    return NULL;
}

static void *student(void *arg) {
    int id = (int)(intptr_t)arg;
    for (;;) {
        wait_sem(&ticks[id]); /* programming: one tick of the model clock */
        pthread_mutex_lock(&mu);
        if (stopping) {
            pthread_mutex_unlock(&mu);
            break;
        }
        int arrival = KEEP_PROGRAMMING;
        if (now >= due[id]) {
            arrivals++;
            record_event("arrive", id);
            if (current < 0) {
                current = id;
                joined[id] = now;
                arrival = WAKE_TA;
            } else if (waiting_count < chairs) {
                queue[waiting_count++] = id;
                state[id] = WAITING;
                joined[id] = now;
                record_event("queue", id);
                arrival = TAKE_CHAIR;
            } else {
                rejected++;
                due[id] = now + random_between(arrival_min, arrival_max);
                record_event("full_return", id);
            }
        }
        pthread_mutex_unlock(&mu);
        if (arrival == WAKE_TA) {
            sem_post(&work);
            wait_sem(&started);
        }
        sem_post(&ack);
        if (arrival == KEEP_PROGRAMMING) {
            continue;
        }
        if (arrival == TAKE_CHAIR) {
            wait_sem(&called[id]);
            if (is_stopping()) {
                break;
            }
        }
        wait_sem(&done[id]);
        pthread_mutex_lock(&mu);
        if (stopping) {
            pthread_mutex_unlock(&mu);
            break;
        }
        state[id] = PROGRAMMING;
        due[id] = now + random_between(arrival_min, arrival_max);
        record_event("program", id);
        pthread_mutex_unlock(&mu);
        sem_post(&returned);
    }
    return NULL;
}

void sim_close(void) {
    pthread_mutex_lock(&mu);
    stopping = 1;
    pthread_mutex_unlock(&mu);
    if (ta_created) {
        sem_post(&work);
        sem_post(&ta_tick);
        pthread_join(ta, NULL);
    }
    for (int i = 0; i < students_created; i++) {
        sem_post(&ticks[i]);
        sem_post(&called[i]);
        sem_post(&done[i]);
    }
    for (int i = 0; i < students_created; i++) {
        pthread_join(students[i], NULL);
    }
    sem_t *common[] = {&work, &ta_tick, &ack, &started, &returned};
    for (int i = 0; i < common_sems; i++) {
        sem_destroy(common[i]);
    }
    for (int i = 0; i < tick_sems; i++) {
        sem_destroy(&ticks[i]);
    }
    for (int i = 0; i < called_sems; i++) {
        sem_destroy(&called[i]);
    }
    for (int i = 0; i < done_sems; i++) {
        sem_destroy(&done[i]);
    }
    if (journal) {
        fclose(journal);
        journal = NULL;
    }
    free(history);
    history = NULL;
    history_capacity = 0;
    active = common_sems = tick_sems = called_sems = done_sems = 0;
    ta_created = students_created = 0;
}

int sim_init(int count, int seats, int amin, int amax,
             int hmin, int hmax, unsigned seed) {
    if (count < 1 || count > MAX_STUDENTS || seats < 0 || seats > MAX_CHAIRS ||
        amin < 1 || amax < amin || amax > 6000 ||
        hmin < 1 || hmax < hmin || hmax > 6000) {
        return -1;
    }
    FILE *new_journal = tmpfile();
    if (!new_journal) {
        return -2; /* Keep the existing run if temporary storage is unavailable. */
    }
    sim_close();
    journal = new_journal;
    n = count;
    chairs = seats;
    arrival_min = amin;
    arrival_max = amax;
    help_min = hmin;
    help_max = hmax;
    rng = seed;
    order_rng = seed ^ 0x9e3779b9u;
    stopping = now = waiting_count = rejected = completed = arrivals = 0;
    busy = wait_sum = remaining = journal_error = 0;
    current = -1;
    recent_count = recent_next = 0;
    memset(state, 0, sizeof(state));
    memset(visits, 0, sizeof(visits));

    sem_t *common[] = {&work, &ta_tick, &ack, &started, &returned};
    for (int i = 0; i < 5; i++) {
        if (sem_init(common[i], 0, 0) != 0) {
            goto resource_error;
        }
        common_sems++;
    }
    for (int i = 0; i < n; i++) {
        if (sem_init(&ticks[i], 0, 0) != 0) {
            goto resource_error;
        }
        tick_sems++;
        if (sem_init(&called[i], 0, 0) != 0) {
            goto resource_error;
        }
        called_sems++;
        if (sem_init(&done[i], 0, 0) != 0) {
            goto resource_error;
        }
        done_sems++;
        due[i] = random_between(arrival_min, arrival_max);
    }
    if (pthread_create(&ta, NULL, teacher, NULL) != 0) {
        goto resource_error;
    }
    ta_created = 1;
    for (int i = 0; i < n; i++) {
        if (pthread_create(&students[i], NULL, student, (void *)(intptr_t)i) != 0) {
            goto resource_error;
        }
        students_created++;
    }
    active = 1;
    record_event("sleep", -1);
    return 0;

resource_error:
    sim_close();
    return -3;
}

void sim_step(void) {
    if (!active) {
        return;
    }
    pthread_mutex_lock(&mu);
    now++;
    int serving = current >= 0;
    pthread_mutex_unlock(&mu);
    /* Finish existing service before arrivals. Each ack completes a worker's
     * transition. This deliberate ordering makes pause/step reproducible. */
    if (serving) {
        sem_post(&ta_tick);
        wait_sem(&ack);
    }
    /* Only programming students follow the clock. The others are blocked on
     * called[i] or done[i] until the TA signals them. */
    int order[MAX_STUDENTS], count = 0;
    pthread_mutex_lock(&mu);
    for (int i = 0; i < n; i++) {
        if (state[i] == PROGRAMMING && current != i) {
            order[count++] = i;
        }
    }
    pthread_mutex_unlock(&mu);
    /* Real threads reach the lock in no fixed order. A seeded shuffle keeps
     * runs reproducible without serving the same students every tick. */
    for (int i = count - 1; i > 0; i--) {
        int j = random_index(i + 1);
        int swap = order[i];
        order[i] = order[j];
        order[j] = swap;
    }
    for (int k = 0; k < count; k++) {
        sem_post(&ticks[order[k]]);
        wait_sem(&ack);
    }
    /* Detect buffered disk write failures promptly, not only on export. */
    if (!journal_error && fflush(journal) != 0) {
        journal_error = 1;
    }
}

const char *sim_snapshot(void) {
    static char out[8192];
    pthread_mutex_lock(&mu);
    int p = snprintf(out, sizeof(out),
        "{\"tick\":%d,\"current\":%d,\"remaining\":%d,\"arrivals\":%d,"
        "\"rejected\":%d,\"completed\":%d,\"busy\":%d,\"wait_sum\":%d,"
        "\"active\":%d,\"journal_error\":%d,\"queue\":[",
        now, current, remaining, arrivals, rejected, completed, busy, wait_sum,
        active, journal_error);
    for (int i = 0; i < waiting_count; i++) {
        p += snprintf(out + p, sizeof(out) - (size_t)p,
                      "%s%d", i ? "," : "", queue[i]);
    }
    p += snprintf(out + p, sizeof(out) - (size_t)p, "],\"students\":[");
    for (int i = 0; i < n; i++) {
        p += snprintf(out + p, sizeof(out) - (size_t)p,
                      "%s{\"state\":%d,\"visits\":%d}",
                      i ? "," : "", state[i], visits[i]);
    }
    snprintf(out + p, sizeof(out) - (size_t)p, "]}");
    pthread_mutex_unlock(&mu);
    return out;
}

/* The controller calls journal functions only between completed ticks. */
const char *sim_recent_events(void) {
    static char out[RECENT_EVENTS * EVENT_LENGTH + 1];
    size_t offset = 0;
    unsigned first = (recent_next + RECENT_EVENTS - recent_count) % RECENT_EVENTS;
    for (unsigned i = 0; i < recent_count; i++) {
        const char *line = recent[(first + i) % RECENT_EVENTS];
        size_t length = strlen(line);
        memcpy(out + offset, line, length);
        offset += length;
    }
    out[offset] = '\0';
    return out;
}

const char *sim_events(void) {
    if (!journal || journal_error || fflush(journal) != 0) {
        return NULL;
    }
    long size = ftell(journal);
    if (size < 0) {
        return NULL;
    }
    if ((size_t)size + 1 > history_capacity) {
        char *expanded = realloc(history, (size_t)size + 1);
        if (!expanded) {
            return NULL;
        }
        history = expanded;
        history_capacity = (size_t)size + 1;
    }
    if (fseek(journal, 0, SEEK_SET) != 0) {
        return NULL;
    }
    size_t read_count = fread(history, 1, (size_t)size, journal);
    int failed = ferror(journal) || read_count != (size_t)size;
    if (fseek(journal, 0, SEEK_END) != 0 || failed) {
        journal_error = 1;
        return NULL;
    }
    history[read_count] = '\0';
    return history;
}

int sim_export(const char *path) {
    if (!journal || journal_error || fflush(journal) != 0) {
        return -1;
    }
    FILE *out = fopen(path, "wb");
    if (!out) {
        return -1;
    }
    int failed = fputs("tick,event,student,waiting\n", out) == EOF;
    if (fseek(journal, 0, SEEK_SET) != 0) {
        failed = 1;
    } else {
        char buffer[8192];
        size_t count;
        while (!failed && (count = fread(buffer, 1, sizeof(buffer), journal)) > 0) {
            failed = fwrite(buffer, 1, count, out) != count;
        }
        if (ferror(journal)) {
            failed = journal_error = 1;
        }
    }
    if (fseek(journal, 0, SEEK_END) != 0) {
        failed = journal_error = 1;
    }
    if (fclose(out) != 0) {
        failed = 1;
    }
    return failed ? -1 : 0;
}
