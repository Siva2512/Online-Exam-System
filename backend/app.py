import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.database import init_db
from backend.routes.auth import auth_bp
from backend.routes.exams import exams_bp
from backend.routes.results import results_bp
from backend.routes.admin import admin_bp

def create_app():
    frontend_dir = Path(__file__).resolve().parent.parent / 'frontend'

    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path='')
    app.config.from_object(Config)

    # Enable CORS for flexible development (e.g. running frontend on port 8000 and backend on 5000)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(exams_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(admin_bp)

    # AWS ALB / EC2 Healthcheck endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'ExamDesk API',
            'environment': 'AWS EC2 / RDS Ready'
        }), 200

    # Serve static frontend pages seamlessly
    @app.route('/', methods=['GET'])
    def serve_index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:filename>', methods=['GET'])
    def serve_static(filename):
        target_path = Path(app.static_folder) / filename
        if target_path.is_file():
            return send_from_directory(app.static_folder, filename)
        # Fallback to index if route not found
        return send_from_directory(app.static_folder, '404.html'), 404

    # Initialize DB schema and initial seeds
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            print(f"[Warning] DB initialization error: {e}")

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"Starting ExamDesk Server on http://0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
