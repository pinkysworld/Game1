from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FiscalTerms:
    royalty: float
    tax_rate: float
    carbon_tax: float = 0.0


def apply_fiscal_terms(revenue: int, terms: FiscalTerms) -> int:
    after_royalty = revenue * (1 - terms.royalty)
    after_tax = after_royalty * (1 - terms.tax_rate)
    return int(after_tax - terms.carbon_tax)
