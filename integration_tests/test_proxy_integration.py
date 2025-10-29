import random
import time
from typing import Dict, Optional, Tuple

import pytest
import requests

from src.network import ProxyPool
from src.api.flightradar import BASE_URL, HEADERS


def _stage2_probe_fr24(proxies: Dict[str, str]) -> Tuple[bool, Optional[int], Optional[str]]:
    # Minimal FR24 request: a valid airport code with limit=1 and a random tag to avoid caches
    params = {
        "code": "HND",
        "page": 1,
        "limit": 1,
        "plugin[]": "schedule",
        "plugin-setting[schedule][mode]": "departures",
        "_t": str(random.randint(1, 1_000_000)),
    }
    try:
        resp = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=(3.0, 5.0),
            proxies=proxies,
        )
        return (200 <= resp.status_code < 300, resp.status_code, None)
    except Exception as exc:  # noqa: BLE001 - integration
        return (False, None, str(exc))


@pytest.mark.integration
def test_proxy_build_smoke_stage1_stage2() -> None:
    # Only pull the first 30 proxies to keep the test lightweight
    pool, survivors, counts = ProxyPool.build(
        source_url=(
            "https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/http.txt"
        ),
        stage1_url="https://httpbin.org/ip",
        stage2_probe=_stage2_probe_fr24,
        fetch_limit=30,
        survivors_max=10,
        connect_timeout=2.0,
        read_timeout=4.0,
        max_workers=16,
        latency_threshold_ms=2000.0,
        strategy="round_robin",
    )

    # Basic sanity checks; do not assert on specific survivor counts (proxies are volatile)
    assert 0 <= counts["fetched"] <= 30
    assert counts["stage1"] <= counts["fetched"]
    assert counts["stage2"] <= counts["stage1"]
    # Pool should be constructed (maybe empty if no survivors)
    assert pool is not None

