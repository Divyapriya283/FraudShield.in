#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt
[ -f data/transactions.csv ] || python3 src/data_generator.py
[ -f models/model.joblib ] || python3 src/train.py
python3 app.py
