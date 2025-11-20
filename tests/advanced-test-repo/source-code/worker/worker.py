import time
import json
import subprocess
import os
from datetime import datetime

# Security issue: Hardcoded credentials
WORKER_SECRET = 'worker-secret-key-12345'

# Security issue: Command injection in task processing
def process_task(task_data):
    task_type = task_data.get('type')

    if task_type == 'execute':
        # Security issue: Command injection vulnerability
        command = task_data.get('command')
        result = subprocess.check_output(command, shell=True)
        return result.decode()

    elif task_type == 'file_operation':
        # Security issue: Path traversal vulnerability
        filename = task_data.get('filename')
        with open(filename, 'r') as f:
            return f.read()

    return {"status": "unknown_task_type"}

if __name__ == '__main__':
    print("Worker started...")
    while True:
        # Simulate processing tasks
        time.sleep(5)
        print(f"Worker running at {datetime.now()}")