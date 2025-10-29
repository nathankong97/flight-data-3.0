"""Network utilities for outbound HTTP, including proxy support.

Exports:
- ``ProxyPool``: rotation and failure tracking for validated proxies.
- ``fetch_proxy_list``: download and parse an HTTP proxy list.
- ``validate_proxy_generic``: quick reachability probe via a generic endpoint.
- ``validate_proxy_custom``: pluggable validator using a caller-provided function.
"""

from src.network.proxy_pool import (
    ProxyEndpoint,
    ProxyProbe,
    ProxyPool,
    fetch_proxy_list,
    validate_proxy_generic,
    validate_proxy_custom,
)

__all__ = [
    "ProxyEndpoint",
    "ProxyProbe",
    "ProxyPool",
    "fetch_proxy_list",
    "validate_proxy_generic",
    "validate_proxy_custom",
]
