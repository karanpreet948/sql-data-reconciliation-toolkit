FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runs fully offline: no external database or network dependency.
ENTRYPOINT ["python", "-m", "reconciler"]
CMD ["run", "--source-a", "data/system_a_records.csv", "--source-b", "data/system_b_records.csv", "--output", "out/reconciliation_report.csv"]
