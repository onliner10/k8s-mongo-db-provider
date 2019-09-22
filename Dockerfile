FROM python:3.7.4-alpine

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

ENTRYPOINT ["kopf", "run", "main.py"]
