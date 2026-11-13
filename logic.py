import re

VALID_CATEGORIES = ["Chemical", "Biological", "Physical", "Pressure", "Supply"]
# Four zone codes are embedded after WS: WSNTH001, WSSTH12, WSEST7, WSWST123.
STATION_RE = re.compile(r"^WS(NTH|STH|EST|WST)\d{1,3}$")
PARAMETER_RE = re.compile(r"^P\d{2}$")

def dfa_accepts_station(value):
    """DFA simulation for WS + one of four zone tokens + 1..3 digits."""
    s = (value or "").upper()
    # states: q0 --W--> q1 --S--> q2 --zone letters--> qz --digit--> qd1
    if not s.startswith("WS"):
        return False
    rest = s[2:]
    zone = next((z for z in ("NTH", "STH", "EST", "WST") if rest.startswith(z)), None)
    if not zone:
        return False
    digits = rest[len(zone):]
    if not (1 <= len(digits) <= 3):
        return False
    state = "qz"
    for ch in digits:
        if not ch.isdigit():
            return False
        state = "qd"
    return state == "qd"

def dfa_accepts_parameter(value):
    s = (value or "").upper()
    if len(s) != 3 or s[0] != "P":
        return False
    return s[1:].isdigit()

def validate_report(data):
    required = ["reporter_name", "station_code", "parameter_code", "description", "urgency"]
    missing = [x for x in required if not str(data.get(x, "")).strip()]
    if missing:
        return {"valid": False, "message": "Missing required field(s): " + ", ".join(missing),
                "dfa_station": False, "regex_station": False, "dfa_parameter": False, "regex_parameter": False}
    station = str(data["station_code"]).strip().upper()
    parameter = str(data["parameter_code"]).strip().upper()
    ds, rs = dfa_accepts_station(station), bool(STATION_RE.fullmatch(station))
    dp, rp = dfa_accepts_parameter(parameter), bool(PARAMETER_RE.fullmatch(parameter))
    if ds != rs or dp != rp:
        return {"valid": False, "message": "Internal validation mismatch: DFA and regex disagree.",
                "dfa_station": ds, "regex_station": rs, "dfa_parameter": dp, "regex_parameter": rp}
    if not ds or not dp:
        return {"valid": False, "message": "Invalid identifier. Station: WS + zone (NTH/STH/EST/WST) + 1–3 digits; parameter: P + 2 digits.",
                "dfa_station": ds, "regex_station": rs, "dfa_parameter": dp, "regex_parameter": rp}
    return {"valid": True, "message": "Accepted: DFA and regular-expression validation agree.",
            "dfa_station": ds, "regex_station": rs, "dfa_parameter": dp, "regex_parameter": rp}

KEYWORDS = {
    "Chemical": ["chemical", "chlorine", "bleach", "oil", "fuel", "pesticide", "metallic", "toxic", "ph", "smell"],
    "Biological": ["bacteria", "bacterial", "virus", "viral", "algae", "microbial", "sewage", "contamination", "illness", "e coli"],
    "Physical": ["mud", "sediment", "turbid", "turbidity", "colour", "color", "particles", "debris", "cloudy", "dirty"],
    "Pressure": ["pressure", "low flow", "weak flow", "burst", "pipe leak", "leakage", "no pressure"],
    "Supply": ["no water", "water cut", "outage", "supply", "interruption", "shortage", "dry tap"]
}
# Documented deterministic tie order: Chemical > Biological > Pressure > Supply > Physical.
TIE_ORDER = ["Chemical", "Biological", "Pressure", "Supply", "Physical"]

def classify_report(description):
    text = (description or "").lower()
    scores = {cat: sum(1 for word in words if word in text) for cat, words in KEYWORDS.items()}
    best = max(scores.values()) if scores else 0
    if best == 0:
        return "Physical", "No keyword matched; safe default category is Physical."
    winner = next(cat for cat in TIE_ORDER if scores[cat] == best)
    return winner, "Keyword scores: " + ", ".join(f"{k}={scores[k]}" for k in VALID_CATEGORIES) + f". Tie order: {' > '.join(TIE_ORDER)}."

def dispatch_report(db, report_id, category, station_code, priority):
    zone = station_code[2:5]
    # Chemical/Biological always escalate to the zonal quality officer.
    if category in ("Chemical", "Biological"):
        target = db.execute("SELECT * FROM handlers WHERE role='Quality Officer' AND available=1 AND current_load<capacity ORDER BY current_load,id LIMIT 1").fetchone()
        route_key = "QUALITY_OFFICER"
        note = "Immediate escalation: chemical/biological incident."
    else:
        route_key = zone
        target = db.execute("SELECT * FROM handlers WHERE zone=? AND role='Maintenance' AND available=1 AND current_load<capacity ORDER BY current_load,id LIMIT 1", (zone,)).fetchone()
        note = f"Nearest field maintenance team selected using zone lookup: {zone}."
    # Backup fallback for unavailable/full primary. Unknown key also lands in documented queue.
    if not target and route_key != "QUALITY_OFFICER":
        target = db.execute("SELECT * FROM handlers WHERE role='Backup' AND available=1 AND current_load<capacity ORDER BY current_load,id LIMIT 1").fetchone()
        note += " Primary unavailable/full; backup fallback attempted."
    if target:
        db.execute("UPDATE handlers SET current_load=current_load+1 WHERE id=?", (target["id"],))
        db.execute("UPDATE reports SET assigned_handler=?, route_key=?, dispatch_note=?, status='Assigned' WHERE id=?",
                   (target["name"], route_key, note, report_id))
        return {"assigned": target["name"], "route_key": route_key, "status": "Assigned", "note": note}
    note += " No eligible handler; retained in priority-ordered Pending queue for manual escalation."
    db.execute("UPDATE reports SET route_key=?, dispatch_note=?, status='Pending' WHERE id=?", (route_key, note, report_id))
    return {"assigned": None, "route_key": route_key, "status": "Pending", "note": note}
