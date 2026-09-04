## About

CityShield AI is a real-time cyber risk detection system for smart city
traffic and emergency infrastructure, built in 48 hours for **Smart Horizon
2026: International Hackathon, New Horizon College of Engineering**.

### The problem

Smart cities increasingly run traffic signals, ambulance dispatch, and
municipal camera networks over connected IoT infrastructure — dispatch
servers, signal controllers, ambulance GPS trackers, and traffic cameras
communicating over MQTT/HTTPS. That connectivity is also an attack surface:
volumetric floods against traffic control servers, reconnaissance sweeps
ahead of an intrusion, brute-force login attempts against dispatch systems,
GPS/MAC spoofing of vehicle identities, and — the hardest case — forged
signal-preemption requests, where an attacker fakes the "clear the
intersection" signal a real ambulance legitimately sends to get a green
light. That last one can't be caught by a naive rule ("preemption request ⇒
suspicious"), because real ambulances trigger the same flag roughly 13% of
the time. Getting it wrong in either direction either lets an attack through
or cries wolf on a genuine emergency vehicle.

### The approach

The system ingests live telemetry (packet rates, connection metadata, login
attempts, GPS deviation, signal-preemption flags, and more) from four device
classes across four city zones, classifies each event into one of six
categories — `normal` or one of five attack types (`ddos`, `port_scan`,
`brute_force`, `spoofing`, `command_injection`) — and streams the result to
a live operations dashboard in under a second.

Classification runs in one of two modes, chosen automatically at startup:

- **Trained mode** — a `RandomForestClassifier` trained on the full labeled
  dataset, reaching 99.94% accuracy on a held-out test split.
- **Heuristic fallback** — if no trained model is present, a set of
  threshold rules derived directly from the dataset's per-label feature
  distributions (documented inline in `backend/model.py`), independently
  reaching ~99% accuracy without requiring a training step.

The same API contract serves both, so the frontend and simulator never need
to know which mode is active.

### What it detects

| Label | What it means |
|---|---|
| `normal` | Legitimate traffic, including ambulances legitimately requesting signal preemption |
| `ddos` | Volumetric flood — abnormal packet rate / SYN flag counts |
| `port_scan` | Reconnaissance sweep across many destination hosts |
| `brute_force` | Repeated failed login attempts against a device |
| `spoofing` | GPS/MAC identity spoofing, e.g. a forged ambulance tracker |
| `command_injection` | Forged signal-preemption requests — deliberately the hardest to catch, since real ambulances trigger the same flag ~13% of the time |

### The system

Four independently runnable pieces, wired together over HTTP and WebSocket:

- **Simulator** replays a labeled dataset (9,000 rows: 6,930 normal traffic
  events plus 414 examples each of the five attack types) as live traffic,
  posting one event at a time to the backend.
- **Backend** (FastAPI) classifies each event on arrival and broadcasts the
  result to every connected dashboard over WebSocket.
- **Training pipeline** (scikit-learn) produces the trained model from the
  same dataset the heuristic fallback was derived from, so both paths are
  grounded in the same ground truth.
- **Frontend** (React + Leaflet), branded as the **Locus AI** live
  operations console, renders a real-time regional risk map, rolling anomaly
  feed, per-zone threat posture, and an actionable incident queue with a
  downloadable audit log.

### Tech stack

Python, FastAPI, Pydantic, scikit-learn, WebSockets, React, Vite, Leaflet

## Running the Project

### Prerequisites

- Python 3.9+ with `pip`
- Node.js 18+ with `npm`

HOW TO RUN:
###Everything runs locally — no external services or API keys required.

### 1. Backend (FastAPI inference API)

```
bash
cd backend
pip install fastapi uvicorn pydantic websockets scikit-learn
uvicorn main:app --reload --port 8000
```
### 2. Frontend (Locus AI live dashboard)
```
bash
cd frontend
npm install
npm run dev

Open http://localhost:5173. It connects to the backend's /ws feed
automatically and will show "no data yet" until the simulator starts
sending traffic.
```

###3. 3. Simulator (drives live traffic through the pipeline)
```
bash
cd simulator
pip install requests
python simulate.py --interval 0.6 --shuffle --loop

--interval 0.6 paces events at a readable ~1.6/sec (lower it for a
denser feed, raise it for a slower one)
--shuffle randomizes row order instead of streaming the CSV in its
original (heavily label-clustered) order
--loop restarts from the beginning once the dataset is exhausted, so it
runs indefinitely
Run only one instance at a time — a second one streaming
concurrently will double the event rate into the same backend
```
