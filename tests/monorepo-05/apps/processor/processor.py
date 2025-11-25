import yaml
from celery import Celery
import redis

app = Celery('processor', broker='redis://redis:6379/0')
r = redis.Redis(host='redis', port=6379)

@app.task
def process_config(config_data):
    # CRITICAL VULNERABILITY: Unsafe YAML deserialization
    # Allows arbitrary code execution
    config = yaml.load(config_data, Loader=yaml.Loader)
    
    print(f"Processing config: {config}")
    return {"status": "processed", "config": str(config)}

@app.task
def process_batch(batch_id):
    # Simulate batch processing
    print(f"Processing batch: {batch_id}")
    return {"batch_id": batch_id, "status": "completed"}

if __name__ == '__main__':
    app.start()
