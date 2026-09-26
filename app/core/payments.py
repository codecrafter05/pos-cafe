"""Payment methods accepted by the cafe.

In-person sales (web POS and the Sunmi handheld) settle in cash, over Benefit
(Bahrain's national debit network), or on a physical card terminal. `transfer`
stays an online-store value: historical orders keep it and the customer-facing
store still offers bank transfer, but no new in-person order may use it.
"""

from typing import Literal

InPersonPaymentMethod = Literal["cash", "benefit", "card"]

IN_PERSON_PAYMENT_METHODS: tuple[str, ...] = ("cash", "benefit", "card")

PAYMENT_LABELS: dict[str, str] = {
    "cash": "Cash",
    "benefit": "Benefit",
    "card": "Card",
    "transfer": "Bank transfer",
}


def payment_label(value: str | None) -> str:
    """Human label for a stored payment_method, including legacy values."""
    if not value:
        return "—"
    return PAYMENT_LABELS.get(value, value.replace("_", " ").title())
