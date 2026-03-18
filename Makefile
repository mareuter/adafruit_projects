# SPDX-FileCopyrightText: 2024-2026 Michael Reuter
#
# SPDX-License-Identifier: MIT

.PHONY: module clean

module:
	$(MAKE) -C modules all

clean:
	$(MAKE) -C modules clean
