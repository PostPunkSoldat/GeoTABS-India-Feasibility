from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from calc_engine import CalculationEngine, ValidationError
import io, json, os

app = Flask(__name__)
CORS(app)  # Add this line

engine = CalculationEngine()

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status':'ok'})

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json() or {}
    project = data.get('projectName','unnamed')
    inputs = data.get('inputs', {})
    try:
        result = engine.run(inputs)
        return jsonify(result)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error: ' + str(e)}), 500

@app.route('/api/report', methods=['POST'])
def report():
    data = request.get_json() or {}
    project = data.get('projectName','report')
    inputs = data.get('inputs', {})
    res = engine.run(inputs)
    bio = io.BytesIO()
    bio.write(json.dumps(res, indent=2).encode('utf-8'))
    bio.seek(0)
    return send_file(bio, mimetype='application/json', download_name=project + '_report.json', as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)