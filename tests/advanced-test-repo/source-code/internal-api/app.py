# Internal API Service
# This service is internal-only, no external exposure
# Used for internal service communication and data processing

from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/internal/health')
def health_check():
    return jsonify({"status": "healthy", "service": "internal-api"})

@app.route('/internal/data')
def get_internal_data():
    # Process internal data
    return jsonify({"data": "internal data processed"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)