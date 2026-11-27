"""
FraudShield - live fraud-scoring API + analyst dashboard.

Runs on plain Python (no Flask/Streamlit needed):   python app.py
Then open  http://localhost:8000

REST API
  GET  /api/meta            model info + evaluation metrics
  POST /api/score           score one transaction (JSON) -> probability, risk, reasons
  GET  /api/stream?n=10     replay unseen test transactions as a "live feed"
  POST /api/feedback        analyst confirms fraud / genuine (stored for retraining)
  GET  /api/feedback        feedback summary
"""
import csv
import json
import os
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import joblib
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))
from features import FEATURES, build_features, explain, raw_from_form  # noqa: E402

MODEL_DIR, STATIC, REPORTS = (os.path.join(ROOT, d) for d in ("models", "static", "reports"))
FEEDBACK = os.path.join(ROOT, "data", "feedback.csv")

if not os.path.exists(os.path.join(MODEL_DIR, "model.joblib")):
    sys.exit("No trained model found. Run:  python src/data_generator.py  then  python src/train.py")

MODEL = joblib.load(os.path.join(MODEL_DIR, "model.joblib"))
if hasattr(MODEL, "n_jobs"):
    MODEL.n_jobs = 1                      # single-row scoring is faster without thread start-up
META = json.load(open(os.path.join(MODEL_DIR, "meta.json")))
BASELINE = pd.Series(META["baseline"])[FEATURES]
THR, MED = META["threshold"], META["medium_threshold"]
TEST = pd.read_csv(os.path.join(MODEL_DIR, "test_scored.csv"))
RNG = np.random.default_rng()


def risk_band(p):
    if p >= THR:
        return "HIGH", "Block & verify with customer"
    if p >= MED:
        return "MEDIUM", "Step-up auth (OTP / PIN re-entry)"
    return "LOW", "Approve"


def score_raw(raw: dict):
    t0 = time.perf_counter()
    X = build_features(pd.DataFrame([raw]))
    p, reasons = explain(MODEL, X, BASELINE)
    band, action = risk_band(p)
    return {"probability": round(p, 4), "risk": band, "action": action, "reasons": reasons,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}


def stream(n):
    # Demo feed: mostly normal traffic with fraud over-represented (~15%) so alerts appear
    fr, ok = TEST[TEST.is_fraud == 1], TEST[TEST.is_fraud == 0]
    k = int(RNG.binomial(n, 0.15))
    rows = pd.concat([fr.sample(k, random_state=int(RNG.integers(1e9))),
                      ok.sample(n - k, random_state=int(RNG.integers(1e9)))]).sample(frac=1)
    out = []
    for _, r in rows.iterrows():
        res = score_raw(r.to_dict())
        res.update(txn_id=r.txn_id, user_id=r.user_id, txn_type=r.txn_type, amount=r.amount,
                   hour=int(r.hour), is_new_device=int(r.is_new_device),
                   is_new_receiver=int(r.is_new_receiver), actual=int(r.is_fraud),
                   pattern=r.fraud_pattern)
        out.append(res)
    return out


def feedback_summary():
    if not os.path.exists(FEEDBACK):
        return {"total": 0, "confirmed_fraud": 0, "false_alarm": 0}
    df = pd.read_csv(FEEDBACK)
    return {"total": len(df), "confirmed_fraud": int((df.label == "fraud").sum()),
            "false_alarm": int((df.label == "genuine").sum())}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=float).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, folder, name, ctype):
        path = os.path.normpath(os.path.join(folder, name))
        if not path.startswith(folder) or not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._file(STATIC, "index.html", "text/html; charset=utf-8")
        if u.path.startswith("/reports/"):
            return self._file(REPORTS, u.path[len("/reports/"):], "image/png")
        if u.path == "/api/meta":
            return self._send(200, {k: v for k, v in META.items() if k != "baseline"})
        if u.path == "/api/stream":
            n = max(1, min(int(parse_qs(u.query).get("n", ["8"])[0]), 50))
            return self._send(200, stream(n))
        if u.path == "/api/feedback":
            return self._send(200, feedback_summary())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid JSON"})
        if u.path == "/api/score":
            try:
                return self._send(200, score_raw(raw_from_form(body)))
            except (KeyError, ValueError) as e:
                return self._send(400, {"error": f"bad input: {e}. Required: amount, old_balance, "
                                                 "user_avg_amount, hour, txn_type"})
        if u.path == "/api/feedback":
            new = not os.path.exists(FEEDBACK)
            with open(FEEDBACK, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time", "txn_id", "score", "label"])
                w.writerow([datetime.now().isoformat(timespec="seconds"), body.get("txn_id"),
                            body.get("score"), body.get("label")])
            return self._send(200, feedback_summary())
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"FraudShield running ->  http://localhost:{port}   (model: {META['deployed_model']})")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
