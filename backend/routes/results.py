from flask import Blueprint, jsonify, g
from backend.services.auth_service import require_auth
from backend.services.exam_service import (
    get_student_attempts,
    get_student_attempt_detail,
    get_student_dashboard_data
)

results_bp = Blueprint('results', __name__, url_prefix='/api')

@results_bp.route('/results', methods=['GET'])
@require_auth
def list_results():
    """
    Returns only the authenticated student's results.
    If the student hasn't taken any tests, returns an empty list.
    """
    user_id = g.current_user['id']
    attempts = get_student_attempts(user_id)
    return jsonify({
        'success': True,
        'results': attempts
    }), 200


@results_bp.route('/results/<attempt_id>', methods=['GET'])
@require_auth
def get_result(attempt_id):
    """
    Returns detailed attempt results.
    Strictly verifies that the attempt belongs to the logged-in student.
    """
    user_id = g.current_user['id']
    attempt = get_student_attempt_detail(user_id, attempt_id)
    if not attempt:
        return jsonify({'success': False, 'message': 'No result found or unauthorized access.'}), 404
    return jsonify({
        'success': True,
        'result': attempt
    }), 200


@results_bp.route('/results/exam/<exam_id>', methods=['GET'])
@require_auth
def get_result_by_exam(exam_id):
    """
    Returns the student's latest result for a specific exam.
    """
    user_id = g.current_user['id']
    attempt = get_student_attempt_detail(user_id, exam_id)
    if not attempt:
        return jsonify({'success': False, 'message': 'You have not submitted this exam yet.'}), 404
    return jsonify({
        'success': True,
        'result': attempt
    }), 200


@results_bp.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """
    Returns student dashboard statistics.
    """
    user_id = g.current_user['id']
    stats = get_student_dashboard_data(user_id)
    return jsonify({
        'success': True,
        'stats': stats
    }), 200
