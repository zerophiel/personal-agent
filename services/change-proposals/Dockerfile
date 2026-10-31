# Build context is services/ (compose): control.py comes along so the proposal rules are control's own.
FROM python:3.12-slim
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY change-proposals/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY control/control.py change-proposals/proposals.py ./
USER 10001
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"
# no -I: isolated mode would drop /app from sys.path (proposals imports control); only our own code lives there
CMD ["python", "proposals.py"]
