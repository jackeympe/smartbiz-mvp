# SmartBiz Fire - Lead Scoring Module

"""
Implements the Revenue Engine directive scoring algorithm.

## Scoring Rules (Max 100)

| Criterion | Points | Notes |
|-----------|--------|-------|
| Identifiable commercial premises | +20 | Physical location confirmed |
| Clear fire-equipment requirement | +20 | Industry/type indicates need |
| Multiple extinguishers/equipment likely | +15 | Size/premises suggests volume |
| Recurring servicing potential | +15 | Ongoing compliance need |
| Decision-maker identified | +10 | Contact person with authority |
| Phone/WhatsApp available | +10 | Direct contact channel |
| Email available | +10 | Digital contact channel |

## Classification

| Score | Priority |
|-------|----------|
| 80-100 | HIGH |
| 60-79 | MEDIUM |
| 40-59 | LOW |
| <40 | NURTURE/RESEARCH |
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "smartbiz.sqlite"

HIGH_NEED_INDUSTRIES = {
    'restaurant', 'takeaway', 'retail', 'warehouse', 'workshop',
    'motor', 'school', 'childcare', 'office', 'guesthouse',
    'hotel', 'shopping', 'property', 'body_corporate',
    'industrial', 'community', 'church', 'event', 'manufacturing',
    'construction', 'logistics', 'healthcare', 'supermarket',
    'pharmacy', 'auto_dealership', 'auto_manufacturing',
    'distribution_centre', 'food_manufacturing', 'telecommunications',
    'hospitality', 'resort_casino', 'commercial_property', 'corporate_office', 'corporate_campus'
}

SIZE_MULTIPLIER = {
    'micro': 0, 'small': 10, 'medium': 15, 'large': 15,
    'multi_site': 15, 'enterprise': 15,
}

RELEVANCE_SCORE = {
    'critical': 15, 'high': 15, 'mandatory': 15, 'medium': 10,
    'low': 5, 'unknown': 0,
}

def calculate_lead_score(lead: dict) -> tuple[int, str]:
    """Calculate lead score and priority per Revenue Engine directive."""
    score = 0
    
    # Identifiable commercial premises
    if lead.get('location') and str(lead.get('location')).strip():
        score += 20
    
    # Clear fire-equipment requirement (by industry/business_type)
    industry = (lead.get('industry') or '').lower().strip()
    business_type = (lead.get('business_type') or '').lower().strip()
    if industry in HIGH_NEED_INDUSTRIES or business_type in HIGH_NEED_INDUSTRIES:
        score += 20
    
    # Multiple extinguishers likely (estimated size)
    size = (lead.get('estimated_size') or '').lower().strip()
    score += SIZE_MULTIPLIER.get(size, 0)
    
    # Recurring servicing potential
    relevance = (lead.get('fire_safety_relevance') or '').lower().strip()
    score += RELEVANCE_SCORE.get(relevance, 0)
    
    # Decision-maker identified
    if lead.get('job_title') and str(lead.get('job_title')).strip():
        score += 10
    
    # Phone/WhatsApp available
    phone = lead.get('phone') or ''
    whatsapp = lead.get('whatsapp') or ''
    if phone.strip():
        score += 5
    if whatsapp.strip():
        score += 5
    
    # Email available
    if lead.get('email') and str(lead.get('email')).strip():
        score += 10
    
    score = min(score, 100)
    
    if score >= 80:
        priority = 'HIGH'
    elif score >= 60:
        priority = 'MEDIUM'
    elif score >= 40:
        priority = 'LOW'
    else:
        priority = 'NURTURE'
    
    return score, priority


def update_lead_score(lead_id: int, score: int, priority: str) -> bool:
    """Update lead score and priority in database."""
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "UPDATE leads SET score=?, lead_status=?, updated_at=? WHERE id=?",
                (score, priority, datetime.now(timezone.utc).isoformat(), lead_id)
            )
            con.commit()
        return True
    except Exception:
        return False


def recalculate_all_lead_scores() -> dict:
    """Recalculate scores for all leads in database."""
    results = {'updated': 0, 'errors': 0}
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM leads").fetchall()
            for row in rows:
                lead = dict(row)
                score, priority = calculate_lead_score(lead)
                con.execute(
                    "UPDATE leads SET score=?, lead_status=?, updated_at=? WHERE id=?",
                    (score, priority, datetime.now(timezone.utc).isoformat(), lead['id'])
                )
                results['updated'] += 1
            con.commit()
    except Exception as e:
        results['errors'] = 1
        results['error_detail'] = str(e)
    return results


def get_leads_by_priority(priority: str = None, limit: int = 50) -> list[dict]:
    """Get leads filtered by priority/score."""
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        if priority:
            rows = con.execute(
                "SELECT * FROM leads WHERE lead_status=? ORDER BY score DESC, created_at DESC LIMIT ?",
                (priority.upper(), limit)
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM leads ORDER BY score DESC, created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_pipeline_summary() -> dict:
    """Get revenue pipeline summary per directive."""
    with sqlite3.connect(DB_PATH) as con:
        # Lead counts by status
        lead_statuses = con.execute(
            "SELECT lead_status, COUNT(*) as count FROM leads GROUP BY lead_status"
        ).fetchall()
        
        # High value opportunities
        high_value = con.execute(
            "SELECT * FROM leads WHERE score >= 80 AND lead_status IN ('QUALIFIED', 'CONTACTED', 'RESPONDED', 'APPOINTMENT') ORDER BY score DESC LIMIT 10"
        ).fetchall()
        
        # Quote pipeline
        quotes = con.execute(
            "SELECT status, COUNT(*) as count, SUM(total_cents) as value FROM quotes GROUP BY status"
        ).fetchall()
        
        # Outstanding payments
        outstanding = con.execute(
            "SELECT SUM(amount_cents) as total FROM bookings WHERE payfast_status != 'paid' AND status NOT IN ('cancelled', 'refunded')"
        ).fetchone()
        
    return {
        'lead_statuses': {row[0]: row[1] for row in lead_statuses if row[0]},
        'high_priority_leads': [dict(r) for r in high_value],
        'quote_pipeline': {row[0]: {'count': row[1], 'value_cents': row[2] or 0} for row in quotes},
        'outstanding_payments_cents': outstanding[0] if outstanding and outstanding[0] else 0,
    }
