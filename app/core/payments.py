"""Payment methods accepted by the cafe.

In-person sales (web POS and the Sunmi handheld) settle in cash or over
Benefit, Bahrain's national debit network. `card` and `transfer` are legacy /
online-store values: historical orders keep them and the customer-facing store
still offers bank transfer, but no new in-person order may use them.
"""

from typing import Literal

InPersonPaymentMethod = Literal["cash", "benefit"]

IN_PERSON_PAYMENT_METHODS: tuple[str, ...] = ("cash", "benefit")

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
