import pytest

from review_contract import ContractError, check_payload


def test_accepts_small_diff():
    assert check_payload({"diff": "+line\n"}) == {
        "valid": True,
        "diff_utf8_bytes": 6,
        "limit_utf8_bytes": 16384,
    }


def test_requires_diff():
    with pytest.raises(ContractError) as error:
        check_payload({})

    assert error.value.code == "diff_required"
