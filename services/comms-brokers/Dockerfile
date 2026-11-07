# The comms zone's two brokers (M4): one image, two containers; compose names each one's module (brokers.gmail,
# brokers.gcal). policy.json is part of the code: what comms may see changes with a rebuild, never at run time.
FROM python:3.12-slim@sha256:6b25cbe6577518889d553cdd5a5da97d259348d8f6e45b527dd731caaba27a07
RUN useradd --system --uid 10003 app
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY brokers ./brokers
USER 10003
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"
# no -I: isolated mode would drop /app from sys.path (python -m brokers.gmail imports the package from there)
CMD ["python", "-m", "brokers.gmail"]
