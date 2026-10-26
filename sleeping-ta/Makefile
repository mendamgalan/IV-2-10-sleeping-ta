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

test: all build/resource_failure
	./build/resource_failure
	$(PYTHON) -m unittest discover -s tests -v

clean:
	rm -f libta.so build/resource_failure

.PHONY: all run test clean
