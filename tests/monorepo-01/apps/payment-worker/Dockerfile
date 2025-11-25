FROM python:3.9-slim
USER daemon
WORKDIR /worker
# Using ADD (just for variety/testing)
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ADD src/ .
CMD ["python", "process.py"]
