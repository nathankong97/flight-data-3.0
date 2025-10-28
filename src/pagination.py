"""Pagination helper mapping airport index to legacy page offsets.

Functions:
    page_for_index(region, index): Return legacy pagination offset based on
        region code and airport index position.
"""


def page_for_index(region: str, index: int) -> int:
    """Return the legacy page offset for a given airport index.

    Args:
        region: Two-letter region code (e.g., 'us', 'jp', 'cn').
        index: Zero-based airport index within the region list.

    Returns:
        The negative legacy page offset used by the upstream pagination.

    Raises:
        ValueError: If ``index`` is negative.
    """

    if index < 0:
        raise ValueError("index must be non-negative")

    count = index
    region_upper = region.upper()

    if region_upper == "US":
        if count <= 10:
            return -15
        if count < 25:
            return -9
        if count <= 60:
            return -4
        return -2

    if region_upper == "JP":
        if count <= 3:
            return -14
        if count <= 5:
            return -9
        return -4

    if region_upper == "CN":
        if count <= 10:
            return -15
        if count <= 20:
            return -9
        if count <= 40:
            return -4
        return -3

    return -1


__all__ = ["page_for_index"]
