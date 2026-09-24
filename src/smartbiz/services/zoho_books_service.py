from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from smartbiz.services.accounting_service import AccountingProvider


class ZohoBooksError(RuntimeError):
    pass


class ZohoBooksProvider(AccountingProvider):
    def __init__(self) -> None:
        self.client_id = os.environ.get("ZOHO_CLIENT_ID", "")
        self.client_secret = os.environ.get("ZOHO_CLIENT_SECRET", "")
        self.refresh_token = os.environ.get("ZOHO_REFRESH_TOKEN", "")
        self.organization_id = os.environ.get("ZOHO_ORGANIZATION_ID", "")
        self.accounts_url = os.environ.get(
            "ZOHO_ACCOUNTS_URL",
            "https://accounts.zoho.in",
        )
        self.api_domain = os.environ.get(
            "ZOHO_API_DOMAIN",
            "https://www.zohoapis.in",
        )

    def configured(self) -> bool:
        return all([
            self.client_id,
            self.client_secret,
            self.refresh_token,
            self.organization_id,
        ])

    def _access_token(self) -> str:
        if not self.configured():
            raise ZohoBooksError("Zoho Books is not configured")

        params = urllib.parse.urlencode({
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode()

        request = urllib.request.Request(
            f"{self.accounts_url}/oauth/v2/token",
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise ZohoBooksError(
                f"Zoho OAuth refresh failed: {detail}"
            ) from exc
        except Exception as exc:
            raise ZohoBooksError(
                f"Zoho OAuth refresh failed: {exc}"
            ) from exc

        token = payload.get("access_token")
        if not token:
            raise ZohoBooksError(
                f"Zoho OAuth response did not contain access_token: {payload}"
            )

        return token

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = self._access_token()

        query = dict(query or {})
        query["organization_id"] = self.organization_id

        url = (
            f"{self.api_domain}/books/v3/{path.lstrip('/')}"
            f"?{urllib.parse.urlencode(query)}"
        )

        body = None
        headers = {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Accept": "application/json",
        }

        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise ZohoBooksError(
                f"Zoho Books API failed ({exc.code}): {detail}"
            ) from exc
        except Exception as exc:
            raise ZohoBooksError(
                f"Zoho Books API failed: {exc}"
            ) from exc

        if data.get("code", 0) not in (0, "0"):
            raise ZohoBooksError(
                f"Zoho Books returned error: {data}"
            )

        return data

    def create_customer(self, customer: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "contacts", customer)

    def create_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "invoices", invoice)

    def record_payment(self, payment: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "customerpayments", payment)

    def create_credit_note(
        self,
        credit_note: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request("POST", "creditnotes", credit_note)


def get_accounting_provider() -> AccountingProvider:
    return ZohoBooksProvider()
