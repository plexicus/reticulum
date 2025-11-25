from flask import Flask, request, jsonify
import yaml
import pickle

app = Flask(__name__)

# HIGH SEVERITY: Unsafe deserialization
@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.data
    # Vulnerable: unsafe YAML load allows arbitrary code execution
    config = yaml.load(data, Loader=yaml.Loader)
    return jsonify({'status': 'imported', 'config': str(config)})

# HIGH SEVERITY: Pickle deserialization
@app.route('/api/restore', methods=['POST'])
def restore():
    data = request.data
    # Vulnerable: pickle can execute arbitrary code
    obj = pickle.loads(data)
    return jsonify({'status': 'restored'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
