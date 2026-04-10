from assistant.backend.utils.logging import sanitize_amount, setup_logging


def test_sanitize_amount_masks_decimals():
    text = "用户今天花了 123.45 元买午餐"
    result = sanitize_amount(text)
    assert "123.45" not in result
    assert "XXX.XX" in result


def test_sanitize_amount_no_amount():
    text = "没有金额的文本"
    result = sanitize_amount(text)
    assert result == text


def test_sanitize_amount_multiple():
    text = "午餐30.50，打车45.00"
    result = sanitize_amount(text)
    assert "30.50" not in result
    assert "45.00" not in result
    assert result.count("XXX.XX") == 2
