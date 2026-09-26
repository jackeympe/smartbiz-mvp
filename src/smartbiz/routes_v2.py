"""SmartBiz Fire V2 API Routes and Handlers for CRM, Operations, Equipment, Quotes, Certificates, Calendar, WhatsApp."""
import base64
import json
import os
import sqlite3
from typing import Any, Dict
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from smartbiz.db import get_connection, db_lock, init_all_tables
from smartbiz.auth import (
    hash_password, verify_password, create_session_token, verify_session_token,
    seed_default_admin, ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_MANAGER, ROLE_TECHNICIAN, ROLE_CUSTOMER
)
from smartbiz.services.crm_service import (
    create_customer, get_customer, list_customers, create_site, get_site,
    list_sites_for_customer, ensure_customer_and_site_from_lead_or_booking
)
from smartbiz.services.equipment_service import (
    create_equipment, get_equipment_by_id, get_equipment_by_qr,
    list_equipment_for_site, record_equipment_service, generate_qr_code_id
)
from smartbiz.services.quote_service import (
    create_quote, get_quote, approve_quote, generate_quote_pdf
)
from smartbiz.services.inspection_service import (
    create_inspection, get_inspection, complete_inspection, generate_inspection_report_pdf
)
from smartbiz.services.certificate_service import (
    issue_certificate, get_certificate, get_certificate_by_number, generate_certificate_pdf
)
from smartbiz.services.renewal_service import (
    scan_and_generate_renewal_reminders,
    get_certificate_renewal_status,
    list_due_certificate_renewals,
)
from smartbiz.services.calendar_service import get_calendar_provider
from smartbiz.services.appointment_service import check_availability, create_confirmed_appointment
from smartbiz.services.whatsapp_service import (
    handle_incoming_message, send_whatsapp_message, verify_webhook_signature, WHATSAPP_VERIFY_TOKEN
)

def _err(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"detail": msg}, status_code=status)

# --- Authentication Endpoints ---
async def auth_login(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _err("Invalid JSON body")
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return _err("Email and password are required")

    with db_lock, get_connection() as con:
        user_row = con.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)).fetchone()
        if not user_row or not verify_password(password, user_row["password_hash"]):
            return _err("Invalid email or password", 401)
        user = dict(user_row)
        token = create_session_token(user["id"], user["email"], user["role"])
        return JSONResponse({
            "ok": True,
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
            }
        })

async def auth_me(request: Request) -> JSONResponse:
    auth_header = request.headers.get("Authorization") or ""
    token = auth_header.replace("Bearer ", "").strip()
    session = verify_session_token(token)
    if not session:
        return _err("Unauthorized session", 401)
    with db_lock, get_connection() as con:
        user_row = con.execute("SELECT id, email, full_name, role, phone, created_at FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        if not user_row:
            return _err("User not found", 404)
        return JSONResponse({"user": dict(user_row)})

# --- Customers Endpoints ---
async def customers_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        limit = int(request.query_params.get("limit", 100))
        offset = int(request.query_params.get("offset", 0))
        customers = list_customers(limit=limit, offset=offset)
        return JSONResponse({"customers": customers})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        comp = (body.get("company_name") or "").strip()
        contact = (body.get("contact_name") or "").strip()
        email = (body.get("email") or "").strip()
        if not comp or not contact or not email:
            return _err("company_name, contact_name and email are required")
        cust = create_customer(
            company_name=comp,
            contact_name=contact,
            email=email,
            phone=body.get("phone", ""),
            whatsapp_number=body.get("whatsapp_number", ""),
            billing_address=body.get("billing_address", ""),
            vat_number=body.get("vat_number", ""),
            notes=body.get("notes", ""),
        )
        return JSONResponse({"ok": True, "customer": cust})
    return _err("Method not allowed", 405)

async def customer_detail_endpoint(request: Request) -> JSONResponse:
    cust_id = int(request.path_params["customer_id"])
    cust = get_customer(cust_id)
    if not cust:
        return _err("Customer not found", 404)
    return JSONResponse({"customer": cust})

# --- Sites Endpoints ---
async def sites_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        cust_id = request.query_params.get("customer_id")
        if cust_id:
            sites = list_sites_for_customer(int(cust_id))
        else:
            with db_lock, get_connection() as con:
                rows = con.execute("SELECT * FROM sites ORDER BY id DESC LIMIT 200").fetchall()
                sites = [dict(r) for r in rows]
        return JSONResponse({"sites": sites})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        cust_id = int(body.get("customer_id") or 0)
        site_name = (body.get("site_name") or "").strip()
        address = (body.get("address") or "").strip()
        if not cust_id or not site_name or not address:
            return _err("customer_id, site_name and address are required")
        site = create_site(
            customer_id=cust_id,
            site_name=site_name,
            address=address,
            suburb=body.get("suburb", ""),
            city=body.get("city", "Johannesburg"),
            province=body.get("province", "Gauteng"),
            postal_code=body.get("postal_code", ""),
            building_type=body.get("building_type", "Commercial"),
            occupancy_type=body.get("occupancy_type", "Office"),
            contact_person=body.get("contact_person", ""),
            contact_phone=body.get("contact_phone", ""),
        )
        return JSONResponse({"ok": True, "site": site})
    return _err("Method not allowed", 405)

# --- Equipment Endpoints ---
async def equipment_list_create_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        site_id = request.query_params.get("site_id")
        if site_id:
            eqs = list_equipment_for_site(int(site_id))
        else:
            with db_lock, get_connection() as con:
                rows = con.execute("SELECT * FROM equipment ORDER BY id DESC LIMIT 200").fetchall()
                eqs = [dict(r) for r in rows]
        return JSONResponse({"equipment": eqs})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        site_id = int(body.get("site_id") or 0)
        eq_type = (body.get("equipment_type") or "DCP_EXTINGUISHER").strip()
        location = (body.get("location_on_site") or "Main Reception").strip()
        if not site_id:
            return _err("site_id is required")
        eq = create_equipment(
            site_id=site_id,
            equipment_type=eq_type,
            location_on_site=location,
            capacity=body.get("capacity", "4.5kg"),
            serial_number=body.get("serial_number", ""),
            manufacturer=body.get("manufacturer", "SmartBiz"),
            model_year=body.get("model_year", "2025"),
            status=body.get("status", "COMPLIANT"),
            notes=body.get("notes", ""),
        )
        return JSONResponse({"ok": True, "equipment": eq})
    return _err("Method not allowed", 405)

async def equipment_detail_endpoint(request: Request) -> JSONResponse:
    eq_id = int(request.path_params["equipment_id"])
    if request.method == "GET":
        eq = get_equipment_by_id(eq_id)
        if not eq:
            return _err("Equipment not found", 404)
        return JSONResponse({"equipment": eq})
    elif request.method == "PATCH":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        status = body.get("status", "COMPLIANT")
        findings = body.get("findings", "Inspected")
        action = body.get("action_taken", "Tested OK")
        tech_id = int(body.get("technician_id", 0))
        eq = record_equipment_service(
            equipment_id=eq_id,
            technician_id=tech_id,
            service_type=body.get("service_type", "Routine Inspection"),
            findings=findings,
            action_taken=action,
            status=status,
            parts_replaced=body.get("parts_replaced", ""),
        )
        return JSONResponse({"ok": True, "equipment": eq})
    return _err("Method not allowed", 405)

async def equipment_qr_lookup_endpoint(request: Request) -> JSONResponse:
    qr = request.path_params["qr_code"].strip()
    eq = get_equipment_by_qr(qr)
    if not eq:
        return _err("Equipment not found for QR code", 404)
    return JSONResponse({"ok": True, "equipment": eq})

# --- Inspections Endpoints ---
async def inspections_list_create_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        with db_lock, get_connection() as con:
            rows = con.execute("SELECT * FROM inspections ORDER BY id DESC LIMIT 100").fetchall()
            return JSONResponse({"inspections": [dict(r) for r in rows]})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        site_id = int(body.get("site_id") or 0)
        if not site_id:
            return _err("site_id is required")
        insp = create_inspection(
            site_id=site_id,
            technician_id=int(body.get("technician_id") or 0),
            scheduled_date=body.get("scheduled_date"),
            checklist_data=body.get("checklist_data"),
        )
        return JSONResponse({"ok": True, "inspection": insp})
    return _err("Method not allowed", 405)

async def inspection_detail_endpoint(request: Request) -> JSONResponse:
    insp_id = int(request.path_params["inspection_id"])
    insp = get_inspection(insp_id)
    if not insp:
        return _err("Inspection not found", 404)
    return JSONResponse({"inspection": insp})

async def inspection_complete_endpoint(request: Request) -> JSONResponse:
    insp_id = int(request.path_params["inspection_id"])
    try:
        body = await request.json()
    except Exception:
        return _err("Invalid JSON body")
    results = body.get("checklist_results") or []
    summary = body.get("findings_summary", "Inspection completed.")
    recs = body.get("recommendations", "Routine maintenance advised.")
    sig = body.get("signature_url", "")
    insp = complete_inspection(
        inspection_id=insp_id,
        checklist_results=results,
        findings_summary=summary,
        recommendations=recs,
        signature_url=sig,
    )
    return JSONResponse({"ok": True, "inspection": insp})

async def inspection_pdf_endpoint(request: Request) -> JSONResponse:
    insp_id = int(request.path_params["inspection_id"])
    try:
        pdf_bytes = generate_inspection_report_pdf(insp_id)
    except Exception as e:
        return _err(f"Inspection report generation failed: {str(e)}", 500)
    return JSONResponse({
        "inspection_id": insp_id,
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "filename": f"inspection-report-{insp_id}.pdf"
    })

# --- Quotes Endpoints ---
async def quotes_list_create_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        with db_lock, get_connection() as con:
            rows = con.execute("SELECT * FROM quotes ORDER BY id DESC LIMIT 100").fetchall()
            quotes = [dict(r) for r in rows]
            for q in quotes:
                q["line_items"] = json.loads(q["line_items"]) if q.get("line_items") else []
            return JSONResponse({"quotes": quotes})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        cust_id = int(body.get("customer_id") or 0)
        if not cust_id:
            return _err("customer_id is required")
        quote = create_quote(
            customer_id=cust_id,
            site_id=int(body.get("site_id") or 0),
            line_items=body.get("line_items"),
            validity_days=int(body.get("validity_days", 30)),
            terms=body.get("terms", "Standard 30 days."),
        )
        return JSONResponse({"ok": True, "quote": quote})
    return _err("Method not allowed", 405)

async def quote_detail_endpoint(request: Request) -> JSONResponse:
    quote_id = int(request.path_params["quote_id"])
    quote = get_quote(quote_id)
    if not quote:
        return _err("Quote not found", 404)
    return JSONResponse({"quote": quote})

async def quote_approve_endpoint(request: Request) -> JSONResponse:
    quote_id = int(request.path_params["quote_id"])
    try:
        body = await request.json()
    except Exception:
        body = {}
    decision = body.get("decision", "APPROVED").upper()
    quote = approve_quote(quote_id, decision=decision, note=body.get("note", ""))
    return JSONResponse({"ok": True, "quote": quote})

async def quote_pdf_endpoint(request: Request) -> JSONResponse:
    quote_id = int(request.path_params["quote_id"])
    try:
        pdf_bytes = generate_quote_pdf(quote_id)
    except Exception as e:
        return _err(f"Quote PDF generation failed: {str(e)}", 500)
    return JSONResponse({
        "quote_id": quote_id,
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "filename": f"quote-{quote_id}.pdf"
    })

# --- Certificates Endpoints ---
async def certificates_list_create_endpoint(request: Request) -> JSONResponse:
    if request.method == "GET":
        with db_lock, get_connection() as con:
            rows = con.execute("SELECT * FROM certificates ORDER BY id DESC LIMIT 100").fetchall()
            return JSONResponse({"certificates": [dict(r) for r in rows]})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        cust_id = int(body.get("customer_id") or 0)
        site_id = int(body.get("site_id") or 0)
        if not cust_id or not site_id:
            return _err("customer_id and site_id are required")
        cert = issue_certificate(
            customer_id=cust_id,
            site_id=site_id,
            inspection_id=int(body.get("inspection_id") or 0),
            scope=body.get("scope", "Annual Fire Compliance"),
            validity_days=int(body.get("validity_days", 365)),
            signatory_name=body.get("signatory_name", "Senior Inspector"),
            signatory_title=body.get("signatory_title", "SAQCC-Fire Registered Inspector (Reg# 22/064)"),
        )
        return JSONResponse({"ok": True, "certificate": cert})
    return _err("Method not allowed", 405)

async def certificate_detail_endpoint(request: Request) -> JSONResponse:
    cert_id = int(request.path_params["certificate_id"])
    cert = get_certificate(cert_id)
    if not cert:
        return _err("Certificate not found", 404)
    return JSONResponse({"certificate": cert})

async def certificate_verify_endpoint(request: Request) -> JSONResponse:
    cert_num = request.path_params["certificate_number"].strip()
    cert = get_certificate_by_number(cert_num)
    if not cert:
        return _err("Certificate not found or unverified", 404)
    return JSONResponse({
        "ok": True,
        "verified": True,
        "certificate_number": cert["certificate_number"],
        "company_name": cert["company_name"],
        "site_name": cert["site_name"],
        "issue_date": cert["issue_date"],
        "expiry_date": cert["expiry_date"],
        "status": cert["status"],
    })

async def certificate_pdf_endpoint(request: Request) -> JSONResponse:
    cert_id = int(request.path_params["certificate_id"])
    try:
        pdf_bytes = generate_certificate_pdf(cert_id)
    except Exception as e:
        return _err(f"Certificate PDF generation failed: {str(e)}", 500)
    return JSONResponse({
        "certificate_id": cert_id,
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "filename": f"coc-certificate-{cert_id}.pdf"
    })

# --- Calendar Endpoints ---
async def calendar_events_endpoint(request: Request) -> JSONResponse:
    provider = get_calendar_provider()
    if request.method == "GET":
        events = provider.list_events()
        return JSONResponse({"events": events})
    elif request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            return _err("Invalid JSON body")
        title = (body.get("title") or "Fire Inspection").strip()
        start = (body.get("start_time") or "").strip()
        end = (body.get("end_time") or start).strip()
        event = provider.create_event(
            title=title,
            start_time=start,
            end_time=end,
            description=body.get("description", ""),
            customer_id=int(body.get("customer_id", 0)),
            site_id=int(body.get("site_id", 0)),
            technician_id=int(body.get("technician_id", 0)),
        )
        return JSONResponse({"ok": True, "event": event})
    return _err("Method not allowed", 405)

# --- Public Appointment Booking Endpoints ---
async def appointment_availability_endpoint(request: Request) -> JSONResponse:
    start_time = (request.query_params.get("start_time") or "").strip()
    try:
        duration = int(request.query_params.get("duration_minutes") or 90)
        result = check_availability(start_time, duration)
    except (TypeError, ValueError) as exc:
        return _err(str(exc), 422)
    return JSONResponse({"ok": True, **result})


async def appointments_endpoint(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return _err("Invalid JSON body")
    try:
        result = create_confirmed_appointment(body)
    except (TypeError, ValueError) as exc:
        return _err(str(exc), 422)
    if result.get("status") == "UNAVAILABLE":
        return JSONResponse(result, status_code=409)
    return JSONResponse(result, status_code=201)


# --- Renewal & Reminders Endpoints ---
async def renewal_scan_endpoint(request: Request) -> JSONResponse:
    res = scan_and_generate_renewal_reminders()
    return JSONResponse(res)


# --- Certificate Renewal Intelligence ---

async def certificate_renewal_status_endpoint(
    request: Request
) -> JSONResponse:
    certificate_id = int(request.path_params["certificate_id"])

    try:
        result = get_certificate_renewal_status(certificate_id)
    except ValueError as exc:
        return _err(str(exc), 422)

    if not result:
        return _err("Certificate not found", 404)

    return JSONResponse({
        "ok": True,
        "renewal": result,
    })


async def renewals_due_endpoint(
    request: Request
) -> JSONResponse:
    results = list_due_certificate_renewals()

    return JSONResponse({
        "ok": True,
        "count": len(results),
        "renewals": results,
    })


# --- WhatsApp Webhooks ---
async def whatsapp_webhook_endpoint(request: Request) -> Any:
    if request.method == "GET":
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            return Response(challenge, media_type="text/plain")
        return _err("Forbidden verification token", 403)
    elif request.method == "POST":
        body_bytes = await request.body()
        sig = request.headers.get("X-Hub-Signature-256", "")
        if not verify_webhook_signature(body_bytes, sig):
            return _err("Invalid signature", 401)
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        # Parse message structure if standard Meta webhook
        messages = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                val = change.get("value", {})
                for msg in val.get("messages", []):
                    from_num = msg.get("from")
                    text = msg.get("text", {}).get("body", "")
                    if from_num and text:
                        resp = handle_incoming_message(from_num, text)
                        messages.append(resp)
                        # Dispatch reply
                        send_whatsapp_message(from_num, resp["message"])

        return JSONResponse({"ok": True, "processed": len(messages), "responses": messages})
    return _err("Method not allowed", 405)


# --- Pricing Endpoints ---

async def pricing_endpoint(request: Request) -> JSONResponse:
    """Return approved SmartBiz Fire pricing from pricing_config."""
    with db_lock, get_connection() as con:
        rows = con.execute("""
            SELECT
                id,
                service_code,
                service_name,
                service_category,
                unit,
                base_cost_cents,
                markup_pct,
                selling_price_cents,
                vat_applicable,
                vat_rate_pct,
                min_quantity,
                max_quantity,
                effective_from,
                effective_to,
                approval_status,
                approved_by,
                approved_at,
                notes
            FROM pricing_config
            WHERE approval_status = 'APPROVED'
              AND (effective_to IS NULL OR effective_to = '')
            ORDER BY service_category, service_name
        """).fetchall()

        pricing = [dict(row) for row in rows]

        return JSONResponse({
            "ok": True,
            "count": len(pricing),
            "currency": "ZAR",
            "vat_rate_pct": 15.0,
            "pricing": pricing
        })


def get_v2_routes() -> list[Route]:
    """Returns all V2 routes to mount in the application."""
    return [
        Route("/api/v1/auth/login", auth_login, methods=["POST"]),
        Route("/api/v1/auth/me", auth_me, methods=["GET"]),
        Route("/api/v1/customers", customers_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/customers/{customer_id:int}", customer_detail_endpoint, methods=["GET"]),
        Route("/api/v1/sites", sites_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/equipment", equipment_list_create_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/equipment/{equipment_id:int}", equipment_detail_endpoint, methods=["GET", "PATCH"]),
        Route("/api/v1/equipment/qr/{qr_code}", equipment_qr_lookup_endpoint, methods=["GET"]),
        Route("/equipment/{qr_code}", equipment_qr_lookup_endpoint, methods=["GET"]),
        Route("/api/v1/inspections", inspections_list_create_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/inspections/{inspection_id:int}", inspection_detail_endpoint, methods=["GET"]),
        Route("/api/v1/inspections/{inspection_id:int}/complete", inspection_complete_endpoint, methods=["POST"]),
        Route("/api/v1/inspections/{inspection_id:int}/pdf", inspection_pdf_endpoint, methods=["GET"]),
        Route("/api/v1/pricing", pricing_endpoint, methods=["GET"]),
        Route("/api/v1/quotes", quotes_list_create_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/quotes/{quote_id:int}", quote_detail_endpoint, methods=["GET"]),
        Route("/api/v1/quotes/{quote_id:int}/approve", quote_approve_endpoint, methods=["POST"]),
        Route("/api/v1/quotes/{quote_id:int}/pdf", quote_pdf_endpoint, methods=["GET"]),
        Route("/api/v1/certificates", certificates_list_create_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/certificates/{certificate_id:int}", certificate_detail_endpoint, methods=["GET"]),
        Route("/api/v1/certificates/{certificate_id:int}/pdf", certificate_pdf_endpoint, methods=["GET"]),
        Route(
            "/api/v1/certificates/{certificate_id:int}/renewal",
            certificate_renewal_status_endpoint,
            methods=["GET"],
        ),
        Route(
            "/api/v1/renewals/due",
            renewals_due_endpoint,
            methods=["GET"],
        ),
        Route("/api/v1/certificates/verify/{certificate_number}", certificate_verify_endpoint, methods=["GET"]),
        Route("/api/v1/appointments/availability", appointment_availability_endpoint, methods=["GET"]),
        Route("/api/v1/appointments", appointments_endpoint, methods=["POST"]),
        Route("/api/v1/calendar/events", calendar_events_endpoint, methods=["GET", "POST"]),
        Route("/api/v1/renewal/scan", renewal_scan_endpoint, methods=["POST"]),
        Route("/api/v1/webhooks/whatsapp", whatsapp_webhook_endpoint, methods=["GET", "POST"]),
    ]
