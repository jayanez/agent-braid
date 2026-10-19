# SPDX-License-Identifier: AGPL-3.0-only
"""Private immutable-image entrypoint source; never installs or activates a profile."""
import sys
sys.path.insert(0,'/opt/agent-braid/source')
from agent_braid.forecast_admission_worker import main

if __name__ == '__main__':
    raise SystemExit(main())
