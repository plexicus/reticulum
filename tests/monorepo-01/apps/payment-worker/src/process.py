import yaml
import time

def load_config(path):
    # CRITIAL VULNERABILITY: YAML deserialization using unsafe Loader
    with open(path, 'r') as f:
        return yaml.load(f, Loader=yaml.Loader) # Loader=yaml.Loader es el valor por defecto en muchas versiones antiguas y es inseguro.

print("Worker started...")

while True:
    time.sleep(60)