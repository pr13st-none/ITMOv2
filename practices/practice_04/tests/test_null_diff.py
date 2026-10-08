import pytest
from review_contract import ContractError, check_payload

def test_rejects_null_byte():
    with pytest.raises(ContractError) as error:
        check_payload({'diff': '+line' + chr(0)})
    assert error.value.code == 'diff_binary'