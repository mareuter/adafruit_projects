# SPDX-FileCopyrightText: 2024 Michael Reuter
#
# SPDX-License-Identifier: MIT

.PHONY: module

module:
	$(MAKE) -C modules all
