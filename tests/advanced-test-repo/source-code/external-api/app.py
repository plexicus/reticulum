# External API Service
# This service is directly exposed to the internet via Ingress
# HIGH exposure level - critical vulnerabilities here are most dangerous

from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.route('/api/v1/public')
def public_endpoint():
    return jsonify({"message": "Public API endpoint", "service": "external-api"})

@app.route('/api/v1/users')
def users_endpoint():
    # Handle user data - this is exposed to the internet
    return jsonify({"users": ["user1", "user2"]})

@app.route('/api/v1/health')
def health_check():
    return jsonify({"status": "healthy", "service": "external-api", "exposure": "high"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)