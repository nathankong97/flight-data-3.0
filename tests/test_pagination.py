import pytest

from src.pagination import page_for_index


@pytest.mark.parametrize(
    "region,index,expected",
    [
        ("us", 0, -15),
        ("us", 10, -15),
        ("us", 11, -9),
        ("us", 24, -9),
        ("us", 25, -4),
        ("us", 60, -4),
        ("us", 61, -2),
        ("jp", 0, -14),
        ("jp", 5, -14),
        ("jp", 6, -5),
        ("cn", 0, -15),
        ("cn", 10, -15),
        ("cn", 11, -9),
        ("cn", 20, -9),
        ("cn", 21, -4),
        ("cn", 40, -4),
        ("cn", 41, -3),
    ],
)
def test_page_for_index_known_regions(region, index, expected):
    assert page_for_index(region, index) == expected


def test_page_for_index_unknown_region():
    assert page_for_index("xx", 3) == -1


def test_page_for_index_negative_index():
    with pytest.raises(ValueError):
        page_for_index("us", -1)
