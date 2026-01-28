import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Flask application...")

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    try:
        logger.info("Home endpoint called")
        return "✅ Minimal Flask Backend is Running!"
    except Exception as e:
        logger.error(f"Error in home endpoint: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/api/health', methods=['GET'])
def health():
    try:
        logger.info("Health check endpoint called")
        return jsonify({
            "status": "Healthy",
            "message": "Minimal service is running",
            "timestamp": datetime.utcnow().isoformat(),
            "python_version": sys.version,
            "environment": os.environ.get('VERCEL_ENV', 'development')
        }), 200
    except Exception as e:
        logger.error(f"Error in health endpoint: {str(e)}")
        return jsonify({
            "status": "Error",
            "error": str(e),
            "python_version": sys.version
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
