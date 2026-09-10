"""WhatsApp Meta Cloud API integration, webhook parser, 2-way interactive menu flow, and notification templates."""
import hashlib
import hmac
import json
import os
import urllib.request
from typing import Any, Dict, List, Optional
from smartbiz.services.crm_service import ensure_customer_and_site_from_lead_or_booking
from smartbiz.services.equipment_service import get_equipment_by_qr

WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "smartbiz_fire_verify_2026")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")

WHATSAPP_MENU_TEXT = """🔥 *SmartBiz Fire Safety*
South Africa's Fire & Safety Compliance Platform

How can we assist you today? Reply with a number:

1️⃣ *Book Fire Inspection* (Free on-site check)
2️⃣ *Request a Quotation* (Extinguishers, Alarms, Hydrants)
3️⃣ *Check Equipment Status* (Send Equipment QR or ID)
4️⃣ *Verify Certificate of Compliance (COC)*
5️⃣ *Speak to Compliance Officer*
"""

def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verifies HMAC-SHA256 signature from Meta webhook."""
    if not WHATSAPP_APP_SECRET or not signature_header:
        return True  # Development / test mode
    try:
        expected = "sha256=" + hmac.new(WHATSAPP_APP_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature_header, expected)
    except Exception:
        return False

def handle_incoming_message(from_number: str, message_text: str, message_id: str = "") -> Dict[str, Any]:
    """Processes incoming 2-way WhatsApp messages and returns response payload."""
    text = (message_text or "").strip().lower()

    if text in ["hi", "hello", "menu", "start", "help", "hie", "dumelang"]:
        return {
            "recipient": from_number,
            "message": WHATSAPP_MENU_TEXT,
            "action": "SHOW_MENU"
        }
    elif text.startswith("1") or "book" in text:
        return {
            "recipient": from_number,
            "message": "📅 *Book Fire Inspection*\nPlease reply with your:\n1. Company/Building Name\n2. Site Address & City\n3. Preferred Date (e.g. 2026-09-15)\n\nWe will confirm your technician dispatch immediately.",
            "action": "PROMPT_BOOKING"
        }
    elif text.startswith("2") or "quote" in text:
        return {
            "recipient": from_number,
            "message": "📄 *Request Quotation*\nPlease reply with the equipment you need serviced (e.g. '4x 4.5kg DCP extinguishers, 2x Hose Reels').\nOr submit online at: https://smartbizfire.co.za/request-quote",
            "action": "PROMPT_QUOTE"
        }
    elif text.startswith("3") or "sb-fe" in text or "equipment" in text:
        # Check if text contains a QR code
        parts = text.upper().split()
        qr = next((p for p in parts if p.startswith("SB-FE-")), None)
        if qr:
            eq = get_equipment_by_qr(qr)
            if eq:
                status_emoji = "🟢" if eq["status"] == "COMPLIANT" else "🔴"
                msg = f"🧯 *Equipment {eq['qr_code']}*\nType: {eq['equipment_type']} ({eq['capacity']})\nStatus: {status_emoji} {eq['status']}\nLast Service: {eq['last_service_date']}\nNext Due: {eq['next_service_date']}\nLocation: {eq['location_on_site']}"
                return {"recipient": from_number, "message": msg, "action": "EQUIPMENT_LOOKUP"}
        return {
            "recipient": from_number,
            "message": "🔍 *Equipment Lookup*\nPlease reply with your unique Equipment ID (e.g. `SB-FE-000184`) to check service validity.",
            "action": "PROMPT_EQUIPMENT"
        }
    elif text.startswith("4") or "coc" in text or "cert" in text:
        return {
            "recipient": from_number,
            "message": "🛡️ *Certificate Verification*\nTo verify a Certificate of Compliance (COC), reply with your Certificate Number (e.g. `COC-2026-0001`) or visit: https://smartbizfire.co.za/verify",
            "action": "PROMPT_CERT"
        }
    else:
        return {
            "recipient": from_number,
            "message": f"Thank you for contacting SmartBiz Fire. Our safety officer will respond to your message shortly.\n\nReply *MENU* at any time to see options.",
            "action": "DEFAULT_ACK"
        }

def send_whatsapp_message(to_number: str, message: str) -> Dict[str, Any]:
    """Sends WhatsApp message via Meta Cloud API or simulates in local environment."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        # Local mock logging
        return {"ok": True, "mode": "mock", "recipient": to_number, "message": message}

    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number.replace("+", "").strip(),
        "type": "text",
        "text": {"body": message}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": True, "mode": "meta_cloud", "response": data}
    except Exception as e:
        return {"ok": False, "mode": "meta_cloud", "error": str(e)}
