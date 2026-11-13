# ClearWater — Water Quality Incident Reporter

A responsive academic demonstration project implementing the supplied P10 problem statement.

## Technology choice
This build uses **Flask + SQLite + HTML/CSS/JavaScript**. The handout's expected-outcome section explicitly asks for a Flask backend and SQLite database, while the suggested stack mentions MERN. This implementation follows the more specific Flask/SQLite integration requirement and keeps setup beginner-friendly. The UI and API are separated so the frontend can later be migrated to React.

## Requirements
- Python 3.9+
- pip

## Run on Windows
1. Extract the ZIP.
2. Open the extracted `water_quality_incident_reporter` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create and activate a virtual environment:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that terminal, then activate again.

5. Install dependencies:

```powershell
pip install -r requirements.txt
```

6. Start the app:

```powershell
python app.py
```

7. Open http://127.0.0.1:5000 in your browser.

The SQLite database `water_reports.db` is created automatically and seeded with four zone maintenance teams, a quality officer, and a backup team.

## Identifier rules
- Station: `WS` + one supported zone (`NTH`, `STH`, `EST`, `WST`) + 1–3 digits. Example: `WSNTH001`.
- Parameter: `P` + exactly two digits. Example: `P01`.
- Both a hand-written DFA simulation and equivalent regular expressions validate the identifiers. The validation response exposes both outcomes to demonstrate agreement.

## Exactly five categories
Chemical, Biological, Physical, Pressure, Supply.

The keyword classifier counts matching terms. If two or more categories have the same highest score, the documented tie order is: **Chemical > Biological > Pressure > Supply > Physical**. If no keyword matches, the safe default is Physical.

## Routing and dispatch
- Chemical and Biological → available Quality Officer (immediate escalation).
- Physical, Pressure, Supply → maintenance handler selected by the 3-letter zone extracted from the validated station code.
- If the primary handler is unavailable or at capacity → available Backup Response Team.
- If no eligible handler exists → report remains Pending in the queue.
- Critical/Emergency urgency becomes Critical priority; High remains High; otherwise Normal.
- Queue listing is ordered Critical, High, Normal, then submission time.

## Features
- Report submission and inline validation.
- Unique auto-increment report ID.
- Five-category classification and priority.
- Routing-table lookup, availability and capacity check, backup fallback and queue.
- User report tracking by ID.
- Handler availability/capacity management.
- Status updates: Pending, Assigned, In Progress, Resolved.
- Routing and analytics dashboards (category, zone, status).
- SQLite persistence and 15 documented unit tests.

## Run tests
```powershell
python -m unittest discover -s tests -v
```

## API overview
- `POST /api/reports`
- `GET /api/reports`
- `GET /api/reports/<id>`
- `PATCH /api/reports/<id>/status`
- `GET /api/handlers`
- `PATCH /api/handlers/<id>`
- `GET /api/routing`
- `GET /api/analytics`

## Demo walkthrough
1. Submit `WSNTH001`, `P01`, description `chemical smell in drinking water`, urgency `Critical`.
2. Note the generated report ID and Quality Officer escalation.
3. Submit `WSSTH12`, `P02`, description `low pressure and weak flow`, urgency `Normal`.
4. Use Track to look up the report ID.
5. Change a handler to Unavailable or reduce capacity to its current load, then submit another report for that zone to demonstrate backup/queue behavior.
6. Update a report to In Progress and then Resolved.
7. Show analytics and routing queue.

## Notes
This is a classroom prototype, not a production public-health reporting service. It does not perform laboratory analysis or send SMS/email alerts. For production, add authentication, audit logging, data protection, and verified operational routing data.
