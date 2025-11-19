from flask import Flask, request, render_template_string
import subprocess
import pickle
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from backend'

@app.route('/vulnerable')
def vulnerable():
    # VULNERABLE: SQL injection
    username = request.args.get('username', 'guest')
    query = f"SELECT * FROM users WHERE username = '{username}'"

    # VULNERABLE: Command injection
    command = request.args.get('command', 'ls')
    result = subprocess.run(f"echo {command}", shell=True, capture_output=True)

    # VULNERABLE: Insecure deserialization
    data = request.args.get('data', '')
    if data:
        deserialized = pickle.loads(data.encode())

    # VULNERABLE: XSS
    user_input = request.args.get('input', 'safe')
    template = f"<div>{user_input}</div>"

    return render_template_string(template)

@app.route('/secret')
def secret():
    # VULNERABLE: Hardcoded secret
    api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
    return f"API Key: {api_key}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
