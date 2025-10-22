"""Pagination helper mapping airport index to legacy page offsets."""


def page_for_index(region: str, index: int) -> int:
    """Return the legacy page offset for a given airport index."""

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
        if count <= 5:
            return -14
        return -5

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
