# Build context is services/ (compose): control.py comes along so the proposal rules are control's own.
FROM python:3.12-slim@sha256:6b25cbe6577518889d553cdd5a5da97d259348d8f6e45b527dd731caaba27a07
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY change-proposals/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY control/control.py change-proposals/proposals.py ./
USER 10001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"
# no -I: isolated mode would drop /app from sys.path (proposals imports control); only our own code lives there
CMD ["python", "proposals.py"]
