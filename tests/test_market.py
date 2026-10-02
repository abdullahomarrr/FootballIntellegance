from decimal import Decimal

from football_intelligence.market import parse_transfer_fee


def test_fee_parser_preserves_semantics_and_currency():
    assert parse_transfer_fee("€12.5m").amount == Decimal("12500000.0")
    assert parse_transfer_fee("£750k").currency == "GBP"
    assert parse_transfer_fee("Free transfer").status == "FREE"
    assert parse_transfer_fee("Loan").status == "LOAN"
    assert parse_transfer_fee("Undisclosed").disclosed is False
    assert parse_transfer_fee("swap plus clauses").status == "UNPARSED"
