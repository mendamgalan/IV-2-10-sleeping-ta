CC = gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -pthread
all: libta.so
libta.so: src/engine.c
	$(CC) $(CFLAGS) -fPIC -shared $< -o $@
run: all
	python3 src/app.py
test: all
	python3 -m unittest discover -s tests -v
clean:
	rm -f libta.so
.PHONY: all run test clean
