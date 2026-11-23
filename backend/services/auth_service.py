import re
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from backend.config import Config
from backend.database import query_db, execute_db

serializer = URLSafeTimedSerializer(Config.SECRET_KEY)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


def generate_token(user_id, email, role):
    """Generates a cryptographically signed authentication token."""
    return serializer.dumps({
        'user_id': user_id,
        'email': email,
        'role': role
    })


def verify_token(token):
    """Verifies a signed token and returns the payload if valid."""
    try:
        data = serializer.loads(token, max_age=Config.TOKEN_EXPIRATION_SECONDS)
        return data
    except (SignatureExpired, BadSignature):
        return None


def register_user(name, email, registration_number, password, department='Computer Science'):
    """
    Registers a new student account after validating all fields.
    Guarantees unique email and unique registration number.
    """
    name = (name or '').strip()
    email = (email or '').strip().lower()
    reg_no = (registration_number or '').strip().upper()
    password = password or ''

    if not name or len(name) < 2:
        return {'success': False, 'message': 'Please enter your full name.'}, 400

    if not reg_no:
        return {'success': False, 'message': 'Please enter a valid registration number.'}, 400

    if not email or not EMAIL_REGEX.match(email):
        return {'success': False, 'message': 'Please enter a valid email address.'}, 400

    if not password or len(password) < 6:
        return {'success': False, 'message': 'Password must be at least 6 characters long.'}, 400

    # Check for duplicate email
    existing_email = query_db("SELECT id FROM users WHERE LOWER(email) = %s", (email,), one=True)
    if existing_email:
        return {'success': False, 'message': 'An account with this email address already exists.'}, 409

    # Check for duplicate registration number
    existing_reg = query_db("SELECT id FROM users WHERE UPPER(registration_number) = %s", (reg_no,), one=True)
    if existing_reg:
        return {'success': False, 'message': 'This registration number is already registered.'}, 409

    # Hash password securely
    pw_hash = generate_password_hash(password)

    user_id, _ = execute_db(
        "INSERT INTO users (name, email, registration_number, password_hash, role, department) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, email, reg_no, pw_hash, 'student', department)
    )

    token = generate_token(user_id, email, 'student')
    user_data = {
        'id': user_id,
        'name': name,
        'email': email,
        'registration_number': reg_no,
        'role': 'student',
        'department': department
    }

    return {
        'success': True,
        'message': 'Account created successfully.',
        'user': user_data,
        'token': token
    }, 201


def login_user(email, password):
    """
    Authenticates a user by email and password hash check.
    """
    email = (email or '').strip().lower()
    password = password or ''

    if not email or not password:
        return {'success': False, 'message': 'Please enter both email and password.'}, 400

    user = query_db("SELECT * FROM users WHERE LOWER(email) = %s", (email,), one=True)
    if not user or not check_password_hash(user['password_hash'], password):
        return {'success': False, 'message': 'The email or password is incorrect. Check both and try again.'}, 401

    token = generate_token(user['id'], user['email'], user['role'])
    user_data = {
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'registration_number': user['registration_number'],
        'role': user['role'],
        'department': user.get('department', 'Computer Science')
    }

    return {
        'success': True,
        'message': 'Login successful.',
        'user': user_data,
        'token': token
    }, 200


def require_auth(f):
    """Decorator to verify bearer token on protected API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif request.args.get('token'):
            token = request.args.get('token').strip()

        if not token:
            return jsonify({'success': False, 'message': 'Authentication required. Missing token.'}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'message': 'Session expired or invalid token. Please log in again.'}), 401

        user = query_db("SELECT id, name, email, registration_number, role, department FROM users WHERE id = %s", (payload['user_id'],), one=True)
        if not user:
            return jsonify({'success': False, 'message': 'User account not found.'}), 401

        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def require_role(role):
    """Decorator to verify that current user has a specific role (e.g. 'admin')."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.current_user.get('role') != role:
                return jsonify({'success': False, 'message': f'Access denied: {role} privileges required.'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

