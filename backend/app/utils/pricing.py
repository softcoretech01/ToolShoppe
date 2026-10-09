from decimal import Decimal, ROUND_HALF_UP


def round_decimal(value: Decimal, places: int = 2) -> Decimal:
    """Round a Decimal to specified decimal places using ROUND_HALF_UP."""
    q = Decimal("10") ** -places
    return value.quantize(q, rounding=ROUND_HALF_UP)


def compute_customer_price(cost: Decimal, markup_pct: Decimal) -> Decimal:
    """
    Customer Price = Cost + Markup
    Example:
    Cost = 615, Markup = 15% -> 615 * 1.15 = 707.25
    """
    cost_dec = Decimal(str(cost))
    markup_dec = Decimal(str(markup_pct))
    price = cost_dec * (Decimal("1.0") + (markup_dec / Decimal("100.0")))
    return round_decimal(price, 2)


def compute_margin_pct(selling_price: Decimal, cost: Decimal) -> Decimal:
    """
    Margin Formula:
    Margin % = ((Selling Price − Cost) ÷ Selling Price) × 100
    Updates instantly when selling price changes.
    """
    sp_dec = Decimal(str(selling_price))
    cost_dec = Decimal(str(cost))
    if sp_dec <= Decimal("0.0"):
        return Decimal("0.00")
    margin = ((sp_dec - cost_dec) / sp_dec) * Decimal("100.0")
    return round_decimal(margin, 2)
