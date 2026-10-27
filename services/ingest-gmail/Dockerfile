FROM python:3.12-slim
RUN useradd --system --uid 10002 ingest
WORKDIR /app
COPY ingest_gmail ./ingest_gmail
USER 10002
CMD ["python", "-m", "ingest_gmail"]
