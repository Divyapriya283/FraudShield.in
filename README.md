# FraudShield: Real-Time Fraud Detection for UPI & Digital Payments

An ML prototype that scores each digital-payment transaction in real time, sorts it into
**Low / Medium / High** risk, and **explains why** it was flagged. An analyst dashboard
shows live alerts and lets the analyst give feedback that can be used for retraining.

**Live demo:** `https://<your-username>.github.io/FraudShield/` (online dashboard, model runs in the browser)

**Full app + API:** `https://<your-app>.onrender.com`. See [DEPLOY.md](DEPLOY.md) for how to deploy.

![Live monitor](screenshots/1_live_monitor.png)

## Quick start (about 2 minutes)

You need Python 3.9+ and four common libraries. Flask and Streamlit are **not** needed.

```bash
pip install -r requirements.txt

python src/data_generator.py      # 1. create ~1.7 lakh synthetic transactions  (~15 s)
python src/train.py               # 2. train + compare models, save charts       (~30 s)
python app.py                     # 3. start the dashboard + API
```

Open **http://localhost:8000** and press **Start live feed**.

On Windows you can double-click `run.bat` instead. On Mac or Linux, run `bash run.sh`.
Steps 1–2 only need to run once. After that, `python app.py` is enough to start the demo.
(The model is trained on your own machine so it always matches your scikit-learn version.)

## Demo script for the presentation (3 minutes)

1. **Live monitor**: press *Start live feed*. Transactions stream in, and high-risk ones show a red badge.
   Click a HIGH row to show the reasons (for example, "Spends 92% of balance", "New device", "70× usual spend").
   Click *Confirm fraud* to show the feedback loop.
2. **Check a transaction**: click *Normal grocery payment* (LOW), then *Account takeover* (HIGH),
   then *"KYC update" scam* (the subtle case, still caught).
3. **Model performance**: walk through the comparison table, explain why accuracy is misleading,
   show the PR curves, the confusion matrix, and recall by fraud type.

## Results (test set = the most recent 15% of time, never seen in training)

| Model | PR-AUC | ROC-AUC | Precision | Recall |
|---|---|---|---|---|
| Logistic Regression (baseline) | 0.776 | 0.995 | 22.6% | 93.9% |
| **Random Forest (deployed)** | **0.900** | 0.993 | 33.1% | **94.8%** |
| Gradient Boosting | 0.877 | 0.981 | 26.3% | 94.8% |
| Isolation Forest (unsupervised) | 0.767 | 0.974 | 52.1% | 75.6% |
| Hybrid (GB + IF) | 0.886 | 0.987 | 28.7% | 94.8% |

- The deployed model catches **109 of 115** frauds in the test period, with 220 false alarms out of about 28,000 genuine payments (0.8%).
- Recall by fraud type: account takeover 100%, mule cash-out 97%, social-engineering scam 81%.
- A model that always says "not fraud" would be **99.6% accurate** while catching nothing. That is why PR-AUC and recall are used instead of accuracy.

Exact numbers can change slightly if you regenerate the data with a different seed.

## Project structure

```
fraudshield/
├── app.py                  REST API + dashboard server (pure Python standard library)
├── src/
│   ├── data_generator.py   synthetic UPI transactions with 3 injected fraud patterns
│   ├── features.py         real-time feature engineering + explanation engine
│   └── train.py            model training, comparison, cost-based threshold, charts
│   └── export_web_model.py exports a light model to docs/ for the browser demo
├── static/index.html       analyst dashboard (HTML/JS)
├── docs/                   GitHub Pages online demo (model runs in the browser)
├── models/                 created by train.py: model, metrics (meta.json), scored test set
├── reports/                charts (PNG) + comparison tables (CSV) for your report
├── data/                   created by data_generator.py: dataset + analyst feedback.csv
├── screenshots/            dashboard screenshots for your report or PPT
├── render.yaml             one-click deploy config for Render
├── Dockerfile              container for IBM Cloud Code Engine / any Docker host
└── DEPLOY.md               step-by-step deployment guide
```

## Methodology (for the report and viva)

**1. Data.** Real bank data is confidential, so like the well-known *PaySim* dataset, we simulate
6,000 users over 60 days (about 1.69 lakh transactions, 0.45% fraud) with realistic spending habits,
and inject three fraud patterns:

| Pattern | Behaviour |
|---|---|
| Account takeover | new device, often at night, drains 50–98% of the balance to new receivers |
| Social-engineering scam | victim's own device, daytime, pays 2.5–10× their normal amount to a new receiver (hardest to catch) |
| Mule cash-out | rapid burst of 3–5 transfers or cash-outs within minutes |

Genuine "noise" (rent payments, big purchases, a new phone) is added so the task is not trivially easy.

**2. Real-time features.** Every feature uses only the user's *past* history at the moment of payment, so there is no data leakage:
amount vs the user's average, share of balance spent, transaction velocity (last 1 h and 24 h), minutes since
the last transaction, new receiver, new device, night-time flag, hour, and transaction type.

**3. Time-based split.** The model trains on days 1–42, the threshold is tuned on the next block of days, and testing uses the last block. This mimics
real deployment (the model predicts the future) and is stricter than a random split.

**4. Class imbalance.** Three strategies are compared: no handling, class weights, and undersampling.
With the default 0.5 threshold, the unhandled model catches only 76% of fraud. Class weights raise this to 94%.

**5. Cost-sensitive threshold.** Missing a fraud is assumed to cost 25× more than a false alarm. The
threshold that minimises total cost on validation data is chosen. You can change `COST_MISSED_FRAUD` in `train.py`.

**6. Risk bands.** HIGH means block and call the customer. MEDIUM means step-up authentication (OTP or PIN), so genuine
users are not blocked outright. LOW means approve.

**7. Explainability.** For each alert, every feature is swapped with the value of a typical genuine
transaction, and the drop in fraud probability is measured. The biggest drops are the reasons shown to the analyst.
This is a lightweight *what-if / perturbation* explanation (the same idea as SHAP, but with no extra library).
Global importance uses permutation importance.

**8. Hybrid idea.** Isolation Forest needs no labels, so it can flag *new* fraud types that the supervised model has never seen.
That is why it is included in the comparison.

## REST API

```bash
curl -X POST http://localhost:8000/api/score -H "Content-Type: application/json" -d '{
  "amount": 46000, "old_balance": 50000, "user_avg_amount": 1200,
  "txn_type": "P2P_TRANSFER", "hour": 2, "mins_since_last_txn": 3,
  "txn_count_1h": 1, "txn_count_24h": 1, "is_new_receiver": true, "is_new_device": true}'
```
Response: `{"probability": 0.98, "risk": "HIGH", "action": "Block & verify with customer", "reasons": [...], "latency_ms": 25}`

Other endpoints: `GET /api/meta`, `GET /api/stream?n=10`, `POST /api/feedback`, `GET /api/feedback`.

## IBM Cloud / watsonx angle

- **Training**: run `src/train.py` as a notebook in **IBM watsonx.ai / Watson Studio** (upload the CSV to a project).
- **Deployment**: save the model to the **watsonx.ai deployment space** for an online scoring endpoint, or containerise `app.py`
  and deploy it on **IBM Cloud Code Engine** (it reads the `PORT` environment variable).
- **Monitoring**: **watsonx.governance (OpenScale)** can track drift and fairness. This prototype already logs analyst feedback for that loop.

## Limitations and future work

- Synthetic data. The next step is validating on the PaySim or Kaggle IEEE-CIS datasets.
- Graph features to detect mule-account rings (sender–receiver networks).
- Automatic retraining from `feedback.csv` and drift alerts.
- Device fingerprinting and geolocation features.
