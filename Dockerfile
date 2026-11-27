# Used for IBM Cloud Code Engine (or any Docker host)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python src/data_generator.py && python src/train.py
ENV PORT=8080
EXPOSE 8080
CMD ["python", "app.py"]
