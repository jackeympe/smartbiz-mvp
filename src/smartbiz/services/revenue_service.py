"""SmartBiz Fire revenue command-centre service."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from smartbiz.db import get_connection, db_lock


OPEN_QUOTE_STAGES = (
    "DRAFT",
    "SENT",
    "VIEWED",
    "PENDING",
    "FOLLOW_UP",
    "FOLLOW-UP",
    "NEGOTIATION",
    "OPEN",
)

WON_STAGES = ("WON", "APPROVED", "ACCEPTED")


def _money(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def get_revenue_dashboard() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    renewal_cutoff = (now.date() + timedelta(days=90)).isoformat()

    result: Dict[str, Any] = {
        "generated_at": now.isoformat(),
        "kpis": {
            "leads_today": 0,
            "total_leads": 0,
            "opportunity_value_cents": 0,
            "open_quotes": 0,
            "open_quote_value_cents": 0,
            "booked_revenue_cents": 0,
            "invoiced_revenue_cents": 0,
            "cash_collected_cents": 0,
            "delivered_job_value_cents": 0,
            "upcoming_appointments": 0,
            "renewals_90_days": 0,
        },
        "pipeline": {},
        "actions": [],
        "quotes": [],
        "appointments": [],
        "renewals": [],
    }

    with db_lock, get_connection() as con:

        # --------------------------------------------------
        # LEADS
        # --------------------------------------------------
        result["kpis"]["total_leads"] = con.execute(
            "SELECT COUNT(*) FROM leads"
        ).fetchone()[0]

        result["kpis"]["leads_today"] = con.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE substr(created_at, 1, 10) = ?
            """,
            (today,),
        ).fetchone()[0]

        result["kpis"]["opportunity_value_cents"] = _money(
            con.execute(
                """
                SELECT COALESCE(SUM(opportunity_value_cents), 0)
                FROM leads
                WHERE UPPER(COALESCE(lead_status, status, 'NEW'))
                      NOT IN ('LOST','CLOSED','DISQUALIFIED')
                """
            ).fetchone()[0]
        )

        for row in con.execute(
            """
            SELECT UPPER(COALESCE(lead_status, status, 'NEW')) AS stage,
                   COUNT(*) AS total
            FROM leads
            GROUP BY UPPER(COALESCE(lead_status, status, 'NEW'))
            """
        ).fetchall():
            result["pipeline"][row["stage"]] = row["total"]

        lead_rows = con.execute(
            """
            SELECT *
            FROM leads
            WHERE UPPER(COALESCE(lead_status, status, 'NEW'))
                  NOT IN ('WON','LOST','CLOSED','DISQUALIFIED')
            ORDER BY
                CASE
                    WHEN UPPER(COALESCE(lead_status,status,'NEW'))='NEW'
                    THEN 0 ELSE 1
                END,
                score DESC,
                id DESC
            LIMIT 25
            """
        ).fetchall()

        for row in lead_rows:
            lead = dict(row)
            stage = (
                lead.get("lead_status")
                or lead.get("status")
                or "NEW"
            ).upper()

            result["actions"].append({
                "type": "LEAD",
                "priority": "HIGH" if stage == "NEW" else "NORMAL",
                "id": lead["id"],
                "title": (
                    lead.get("next_action")
                    or ("Call new lead" if stage == "NEW" else "Follow up lead")
                ),
                "customer": " ".join(
                    filter(None, [lead.get("first_name"), lead.get("last_name")])
                ),
                "company": lead.get("company") or "",
                "phone": lead.get("phone") or lead.get("whatsapp") or "",
                "status": stage,
                "value_cents": _money(lead.get("opportunity_value_cents")),
                "probability_pct": _money(lead.get("probability_pct")),
                "assigned_agent": lead.get("assigned_agent") or "",
            })

        # --------------------------------------------------
        # QUOTES / REVENUE
        # --------------------------------------------------
        placeholders = ",".join("?" for _ in OPEN_QUOTE_STAGES)

        result["kpis"]["open_quotes"] = con.execute(
            f"""
            SELECT COUNT(*)
            FROM quotes
            WHERE UPPER(COALESCE(quote_stage,status,'DRAFT'))
                  IN ({placeholders})
            """,
            OPEN_QUOTE_STAGES,
        ).fetchone()[0]

        result["kpis"]["open_quote_value_cents"] = _money(
            con.execute(
                f"""
                SELECT COALESCE(SUM(total_cents),0)
                FROM quotes
                WHERE UPPER(COALESCE(quote_stage,status,'DRAFT'))
                      IN ({placeholders})
                """,
                OPEN_QUOTE_STAGES,
            ).fetchone()[0]
        )

        revenue = con.execute(
            """
            SELECT
                COALESCE(SUM(booked_value_cents),0) AS booked,
                COALESCE(SUM(invoiced_value_cents),0) AS invoiced,
                COALESCE(SUM(collected_cash_cents),0) AS collected,
                COALESCE(SUM(delivered_job_value_cents),0) AS delivered
            FROM quotes
            """
        ).fetchone()

        result["kpis"]["booked_revenue_cents"] = _money(revenue["booked"])
        result["kpis"]["invoiced_revenue_cents"] = _money(revenue["invoiced"])
        result["kpis"]["cash_collected_cents"] = _money(revenue["collected"])
        result["kpis"]["delivered_job_value_cents"] = _money(revenue["delivered"])

        quote_rows = con.execute(
            """
            SELECT
                q.*,
                c.company_name,
                c.contact_name,
                c.phone
            FROM quotes q
            LEFT JOIN customers c ON c.id = q.customer_id
            ORDER BY q.id DESC
            LIMIT 40
            """
        ).fetchall()

        for row in quote_rows:
            q = dict(row)
            stage = (q.get("quote_stage") or q.get("status") or "DRAFT").upper()

            item = {
                "id": q["id"],
                "quote_number": q.get("quote_number") or "",
                "company": q.get("company_name") or "",
                "contact": q.get("contact_name") or "",
                "phone": q.get("phone") or "",
                "status": q.get("status") or "",
                "stage": stage,
                "total_cents": _money(q.get("total_cents")),
                "booked_value_cents": _money(q.get("booked_value_cents")),
                "invoiced_value_cents": _money(q.get("invoiced_value_cents")),
                "collected_cash_cents": _money(q.get("collected_cash_cents")),
                "delivered_job_value_cents": _money(q.get("delivered_job_value_cents")),
                "follow_up_date": q.get("follow_up_date") or "",
                "valid_until": q.get("valid_until") or "",
                "scheduled_date": q.get("scheduled_date") or "",
                "invoice_number": q.get("invoice_number") or "",
                "job_id": q.get("job_id"),
                "created_at": q.get("created_at") or "",
            }

            result["quotes"].append(item)

            if stage in OPEN_QUOTE_STAGES:
                result["actions"].append({
                    "type": "QUOTE",
                    "priority": "HIGH",
                    "id": q["id"],
                    "title": "Follow up quotation",
                    "customer": q.get("company_name") or "",
                    "phone": q.get("phone") or "",
                    "status": stage,
                    "value_cents": _money(q.get("total_cents")),
                    "due": q.get("follow_up_date") or "",
                })

            if stage in WON_STAGES and not q.get("scheduled_date"):
                result["actions"].append({
                    "type": "JOB",
                    "priority": "HIGH",
                    "id": q["id"],
                    "title": "Schedule won job",
                    "customer": q.get("company_name") or "",
                    "phone": q.get("phone") or "",
                    "status": stage,
                    "value_cents": _money(q.get("total_cents")),
                })

            if (
                _money(q.get("invoiced_value_cents")) > 0
                and _money(q.get("collected_cash_cents"))
                    < _money(q.get("invoiced_value_cents"))
            ):
                result["actions"].append({
                    "type": "PAYMENT",
                    "priority": "HIGH",
                    "id": q["id"],
                    "title": "Collect outstanding payment",
                    "customer": q.get("company_name") or "",
                    "phone": q.get("phone") or "",
                    "status": "OUTSTANDING",
                    "value_cents": (
                        _money(q.get("invoiced_value_cents"))
                        - _money(q.get("collected_cash_cents"))
                    ),
                })

        # --------------------------------------------------
        # APPOINTMENTS
        # --------------------------------------------------
        appointment_rows = con.execute(
            """
            SELECT *
            FROM bookings
            WHERE scheduled_start != ''
              AND substr(scheduled_start,1,10) >= ?
            ORDER BY scheduled_start ASC
            LIMIT 30
            """,
            (today,),
        ).fetchall()

        result["kpis"]["upcoming_appointments"] = len(appointment_rows)

        for row in appointment_rows:
            b = dict(row)
            result["appointments"].append({
                "id": b["id"],
                "booking_reference": b.get("booking_reference") or "",
                "customer": " ".join(
                    filter(None, [b.get("first_name"), b.get("last_name")])
                ),
                "company": b.get("company") or "",
                "phone": b.get("phone") or b.get("whatsapp_number") or "",
                "service": b.get("service") or "",
                "status": b.get("status") or "",
                "scheduled_start": b.get("scheduled_start") or "",
                "scheduled_end": b.get("scheduled_end") or "",
                "calendar_event_id": b.get("calendar_event_id") or 0,
                "whatsapp_status": b.get("whatsapp_status") or "",
            })

        # --------------------------------------------------
        # RENEWALS
        # --------------------------------------------------
        renewal_rows = con.execute(
            """
            SELECT
                cert.*,
                c.company_name,
                c.contact_name,
                c.phone,
                s.site_name
            FROM certificates cert
            LEFT JOIN customers c ON c.id = cert.customer_id
            LEFT JOIN sites s ON s.id = cert.site_id
            WHERE cert.expiry_date >= ?
              AND cert.expiry_date <= ?
              AND UPPER(cert.status) != 'REVOKED'
            ORDER BY cert.expiry_date ASC
            LIMIT 50
            """,
            (today, renewal_cutoff),
        ).fetchall()

        result["kpis"]["renewals_90_days"] = len(renewal_rows)

        for row in renewal_rows:
            cert = dict(row)

            try:
                days_remaining = (
                    datetime.fromisoformat(cert["expiry_date"][:10]).date()
                    - now.date()
                ).days
            except Exception:
                days_remaining = None

            renewal = {
                "id": cert["id"],
                "certificate_number": cert.get("certificate_number") or "",
                "company": cert.get("company_name") or "",
                "contact": cert.get("contact_name") or "",
                "phone": cert.get("phone") or "",
                "site": cert.get("site_name") or "",
                "expiry_date": cert.get("expiry_date") or "",
                "days_remaining": days_remaining,
                "status": cert.get("status") or "",
            }

            result["renewals"].append(renewal)

            if days_remaining is not None and days_remaining <= 30:
                result["actions"].append({
                    "type": "RENEWAL",
                    "priority": "HIGH",
                    "id": cert["id"],
                    "title": "Contact customer for renewal",
                    "customer": cert.get("company_name") or "",
                    "phone": cert.get("phone") or "",
                    "status": f"{days_remaining} DAYS",
                    "value_cents": 0,
                })

    priority = {"HIGH": 0, "NORMAL": 1, "LOW": 2}

    result["actions"].sort(
        key=lambda x: (priority.get(x.get("priority"), 9), x.get("id") or 0)
    )

    result["actions"] = result["actions"][:40]

    return result
