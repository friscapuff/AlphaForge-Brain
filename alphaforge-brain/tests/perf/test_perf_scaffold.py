import os
import time

import pytest


@pytest.mark.perf
@pytest.mark.xfail(reason="FR-113 benchmark harness not implemented yet", strict=False)
@pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Perf scaffold skipped in CI until harness lands"
)
def test_perf_scaffold_timer_smoke(rss_sampler):
    """Minimal perf scaffold: measure a small sleep and capture RSS.

    This ensures the perf marker and fixture wiring are correct without
    introducing brittle thresholds. Replaced by FR-113 harness later.
    """
    start = time.perf_counter()
    time.sleep(0.01)
    elapsed = time.perf_counter() - start

    # Best-effort RSS check: make sure fixture returns a float or None
    rss = rss_sampler.rss_mb()
    assert rss is None or isinstance(rss, float)

    # No strict assertion on elapsed; just sanity bound to avoid zeros
    assert elapsed >= 0.0
