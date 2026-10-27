FROM python:3.12-slim
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY control.py .
USER 10001
CMD ["python", "-I", "control.py"]
