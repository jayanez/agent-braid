// SPDX-License-Identifier: AGPL-3.0-only
/* Private source-only hooks. Included only in the separately built FC1 image. */
#pragma once

int fc1_unit_role(const char *unit);
int fc1_gate_open(const char *unit);
int fc1_gate_authorize(int fd, unsigned site, const char *unit, const char *invocation);
