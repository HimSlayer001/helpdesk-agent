FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY kb ./kb
ENV PYTHONPATH=src OLLAMA_URL=http://host.docker.internal:11434
EXPOSE 8000
CMD ["uvicorn", "helpdesk.api:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
