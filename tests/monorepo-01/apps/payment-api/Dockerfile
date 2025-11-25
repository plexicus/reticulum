FROM python:3.9-slim
USER daemon

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Using COPY to add source code
COPY src/ ./src
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]
