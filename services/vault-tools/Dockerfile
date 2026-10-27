FROM python:3.12-slim
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vault_tools ./vault_tools
USER 10001
ENV LEDGER_DB=/data/ledger.db
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"
# no -I: isolated mode would drop /app from sys.path; only our own code lives there
CMD ["python", "-m", "vault_tools.server"]
