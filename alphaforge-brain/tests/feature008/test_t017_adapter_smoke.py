from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason=(
        "T017 adapter smoke test retired in Phase 7 (T070). Adapters removed; "
        "test retained for history but skipped."
    )
)
