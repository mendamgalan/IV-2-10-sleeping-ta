CC = gcc
PYTHON ?= python3
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -pthread

all: libta.so

libta.so: src/engine.c
	$(CC) $(CFLAGS) -fPIC -shared $< -o $@

run: all
	$(PYTHON) src/app.py

build/resource_failure: tests/resource_failure.c src/engine.c
	mkdir -p build
	$(CC) $(CFLAGS) $< -o $@

build/stress: tests/stress.c src/engine.c
	mkdir -p build
	$(CC) $(CFLAGS) $< -o $@

build/stress_tsan: tests/stress.c src/engine.c
	mkdir -p build
	$(CC) -std=c11 -O1 -g -pthread -fsanitize=thread $< -o $@

test: all build/resource_failure build/stress
	./build/resource_failure
	./build/stress
	$(PYTHON) -m unittest discover -s tests -v

# ThreadSanitizer needs a fixed address layout on newer kernels.
tsan: build/stress_tsan
	TSAN_OPTIONS=halt_on_error=1 setarch "$$(uname -m)" -R ./build/stress_tsan 1000

clean:
	rm -f libta.so build/resource_failure build/stress build/stress_tsan

.PHONY: all run test tsan clean
