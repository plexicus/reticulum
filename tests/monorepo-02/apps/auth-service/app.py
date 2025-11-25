from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# CRITICAL VULNERABILITY: SQL Injection
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Vulnerable SQL query - direct string concatenation
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({'success': True, 'token': 'fake-jwt-token'})
    return jsonify({'success': False}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
