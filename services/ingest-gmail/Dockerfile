FROM python:3.12-slim@sha256:6b25cbe6577518889d553cdd5a5da97d259348d8f6e45b527dd731caaba27a07
RUN useradd --system --uid 10002 ingest
WORKDIR /app
COPY ingest_gmail ./ingest_gmail
USER 10002
CMD ["python", "-m", "ingest_gmail"]
