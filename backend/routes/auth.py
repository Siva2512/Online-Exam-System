from flask import Blueprint, request, jsonify, g
from backend.services.auth_service import register_user, login_user, require_auth

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    reg_no = data.get('registration_number') or data.get('sid')
    password = data.get('password')
    department = data.get('department', 'Computer Science')

    res, status_code = register_user(name, email, reg_no, password, department)
    return jsonify(res), status_code


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    res, status_code = login_user(email, password)
    return jsonify(res), status_code


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    return jsonify({
        'success': True,
        'user': g.current_user
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    # Client will clear stored token
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200
