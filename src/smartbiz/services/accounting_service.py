from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AccountingProvider(ABC):
    """Provider-neutral accounting interface used by SmartBiz Fire."""

    @abstractmethod
    def configured(self) -> bool:
        ...

    @abstractmethod
    def create_customer(self, customer: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def create_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def record_payment(self, payment: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def create_credit_note(self, credit_note: dict[str, Any]) -> dict[str, Any]:
        ...


def get_accounting_provider() -> AccountingProvider:
    """
    Return the configured accounting provider.

    Zoho Books is currently the sole accounting provider for SmartBiz Fire.
    The provider import is deliberately lazy to avoid circular imports.
    """
    from smartbiz.services.zoho_books_service import ZohoBooksProvider

    return ZohoBooksProvider()
