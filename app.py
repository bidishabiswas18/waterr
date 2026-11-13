from flask import Flask, render_template, request, jsonify
from database import init_db, get_db
from logic import validate_report, classify_report, dispatch_report, VALID_CATEGORIES
from datetime import datetime

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/meta")
def meta():
    return jsonify({"categories": VALID_CATEGORIES, "zones": ["NTH", "STH", "EST", "WST"]})

@app.post("/api/reports")
def create_report():
    data = request.get_json(silent=True) or request.form.to_dict()
    validation = validate_report(data)
    if not validation["valid"]:
        return jsonify({"ok": False, "validation": validation}), 400

    category, reason = classify_report(data.get("description", ""))
    priority = "Critical" if data.get("urgency", "").lower() in ("critical", "emergency") else (
        "High" if data.get("urgency", "").lower() == "high" else "Normal"
    )
    db = get_db()
    cur = db.execute("""
        INSERT INTO reports(reporter_name, contact, station_code, parameter_code, description,
        urgency, category, priority, status, validation_message, created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (data["reporter_name"].strip(), data.get("contact","").strip(),
          data["station_code"].upper().strip(), data["parameter_code"].upper().strip(),
          data["description"].strip(), data.get("urgency","Normal"), category, priority,
          "Pending", validation["message"], datetime.now().isoformat(timespec="seconds")))
    report_id = cur.lastrowid
    dispatch = dispatch_report(db, report_id, category, data["station_code"].upper().strip(), priority)
    db.commit()
    report = db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    return jsonify({"ok": True, "report": dict(report), "dispatch": dispatch, "classification_reason": reason}), 201

@app.get("/api/reports")
def reports():
    db = get_db()
    rows = db.execute("SELECT * FROM reports ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 ELSE 2 END, created_at DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.get("/api/reports/<int:report_id>")
def get_report(report_id):
    row = get_db().execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(dict(row))

@app.patch("/api/reports/<int:report_id>/status")
def update_status(report_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    allowed = ["Pending", "Assigned", "In Progress", "Resolved"]
    if status not in allowed:
        return jsonify({"error": "Status must be one of: " + ", ".join(allowed)}), 400
    db = get_db()
    cur = db.execute("UPDATE reports SET status=? WHERE id=?", (status, report_id))
    if cur.rowcount == 0:
        return jsonify({"error": "Report not found"}), 404
    db.commit()
    return jsonify({"ok": True, "report": dict(db.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone())})

@app.get("/api/handlers")
def handlers():
    return jsonify([dict(r) for r in get_db().execute("SELECT * FROM handlers ORDER BY id")])

@app.patch("/api/handlers/<int:handler_id>")
def update_handler(handler_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    current = db.execute("SELECT * FROM handlers WHERE id=?", (handler_id,)).fetchone()
    if not current:
        return jsonify({"error": "Handler not found"}), 404
    available = int(bool(data.get("available", current["available"])))
    capacity = max(0, int(data.get("capacity", current["capacity"])))
    db.execute("UPDATE handlers SET available=?, capacity=? WHERE id=?", (available, capacity, handler_id))
    db.commit()
    return jsonify({"ok": True})

@app.get("/api/analytics")
def analytics():
    db = get_db()
    total = db.execute("SELECT COUNT(*) n FROM reports").fetchone()["n"]
    by_category = db.execute("SELECT category label, COUNT(*) value FROM reports GROUP BY category").fetchall()
    by_zone = db.execute("SELECT substr(station_code,3,3) label, COUNT(*) value FROM reports GROUP BY substr(station_code,3,3)").fetchall()
    by_status = db.execute("SELECT status label, COUNT(*) value FROM reports GROUP BY status").fetchall()
    return jsonify({"total": total, "by_category": [dict(x) for x in by_category],
                    "by_zone": [dict(x) for x in by_zone], "by_status": [dict(x) for x in by_status]})

@app.get("/api/routing")
def routing():
    db = get_db()
    active = db.execute("SELECT name, zone, capacity, available FROM handlers ORDER BY zone, name").fetchall()
    queued = db.execute("SELECT id, station_code, category, priority, status, assigned_handler FROM reports WHERE status='Pending' ORDER BY CASE priority WHEN 'Critical' THEN 0 WHEN 'High' THEN 1 ELSE 2 END, created_at").fetchall()
    return jsonify({"handlers": [dict(x) for x in active], "queue": [dict(x) for x in queued]})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
