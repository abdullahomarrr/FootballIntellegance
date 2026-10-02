from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ParsedFee:
    amount: Decimal | None
    currency: str | None
    status: str
    disclosed: bool
    raw_text: str


def parse_transfer_fee(raw: str) -> ParsedFee:
    text = " ".join(raw.strip().split())
    normalized = text.casefold()
    if normalized in {"free", "free transfer", "no fee"}:
        return ParsedFee(Decimal("0"), None, "FREE", True, text)
    if "loan" in normalized:
        return ParsedFee(None, None, "LOAN", False, text)
    if normalized in {"undisclosed", "unknown", "n/a", "-", ""}:
        return ParsedFee(None, None, "UNDISCLOSED", False, text)
    match = re.search(r"([€£$])\s*([0-9]+(?:[.,][0-9]+)?)\s*(m|million|k|thousand)?", text, re.I)
    if not match:
        return ParsedFee(None, None, "UNPARSED", False, text)
    currencies = {"€": "EUR", "£": "GBP", "$": "USD"}
    amount = Decimal(match.group(2).replace(",", "."))
    suffix = (match.group(3) or "").casefold()
    multiplier = (
        Decimal("1000000")
        if suffix in {"m", "million"}
        else Decimal("1000")
        if suffix in {"k", "thousand"}
        else Decimal("1")
    )
    return ParsedFee(amount * multiplier, currencies[match.group(1)], "DISCLOSED", True, text)
