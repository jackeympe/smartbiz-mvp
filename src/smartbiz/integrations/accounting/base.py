from abc import ABC, abstractmethod
from typing import Any


class AccountingProvider(ABC):

    @abstractmethod
    async def create_customer(self, customer: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_credit_note(self, credit_note: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_invoice(self, external_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        raise NotImplementedError
