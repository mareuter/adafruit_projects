# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

.PHONY: clean all

SRCS := $(wildcard *.py)
MODULES := $(SRCS:.py=.mpy)

all: $(MODULES)

%.mpy: %.py
	mpy $<

clean:
	rm *.mpy
