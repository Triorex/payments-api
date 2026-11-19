"""payments-api: a small payments service onboarded to the Triorex paved road.

Deliberately simple so the security controls around it are the point:
  - strict input validation (pydantic) on every field
  - parameterised SQL only (the curation, SAST and DAST demos change this on purpose)
  - security headers on every response, no server banner, no interactive docs in production
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}

MERCHANT_ID = r"^m_[a-z0-9]{6,32}$"
PAYMENT_ID = r"^pay_[0-9a-f]{32}$"


class PaymentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, le=Decimal("1000000"), max_digits=12, decimal_places=2)
    currency: Literal["USD", "EUR", "GBP"]
    merchant_id: str = Field(pattern=MERCHANT_ID)
    description: str = Field(default="", max_length=140)


class Payment(PaymentIn):
    id: str
    status: Literal["authorized"]


class Store:
    """In-memory SQLite. The container runs with a read-only root filesystem, so nothing is written to disk."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(":memory:", check_same_thread=False)
        self._db.execute(
            "CREATE TABLE payments (id TEXT PRIMARY KEY, amount TEXT NOT NULL, currency TEXT NOT NULL, "
            "merchant_id TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL)"
        )

    def add(self, p: PaymentIn) -> Payment:
        payment = Payment(id=f"pay_{uuid.uuid4().hex}", status="authorized", **p.model_dump())
        with self._lock:
            self._db.execute(
                "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?)",
                (payment.id, str(payment.amount), payment.currency, payment.merchant_id, payment.description, payment.status),
            )
        return payment

    def get(self, payment_id: str) -> Payment | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        return self._row(row) if row else None

    def by_merchant(self, merchant_id: str) -> list[Payment]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM payments WHERE merchant_id = ? ORDER BY rowid", (merchant_id,)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(row: tuple) -> Payment:
        pid, amount, currency, merchant_id, description, status = row
        return Payment(id=pid, amount=Decimal(amount), currency=currency, merchant_id=merchant_id, description=description, status=status)


store = Store()
app = FastAPI(title="payments-api", version="1.1.0", docs_url=None, redoc_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/payments", status_code=201, response_model=Payment)
def create_payment(payment: PaymentIn) -> Payment:
    return store.add(payment)


@app.get("/payments/{payment_id}", response_model=Payment)
def get_payment(payment_id: str) -> Payment:
    payment = store.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    return payment


@app.get("/payments", response_model=list[Payment])
def list_payments(merchant_id: str = Query(pattern=MERCHANT_ID)) -> list[Payment]:
    return store.by_merchant(merchant_id)
