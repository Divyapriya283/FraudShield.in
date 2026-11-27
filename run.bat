@echo off
cd /d "%~dp0"
pip install -r requirements.txt
if not exist data\transactions.csv python src\data_generator.py
if not exist models\model.joblib python src\train.py
python app.py
pause
