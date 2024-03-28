# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

.PHONY: module cleam

module:
	$(MAKE) -C modules all

clean:
	$(MAKE) -C modules clean
