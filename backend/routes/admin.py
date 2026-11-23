"""
Admin Route Blueprint:
Protected endpoints for examination administration, question authoring, student monitoring, and report exporting.
"""

from flask import Blueprint, request, jsonify, Response
from backend.services.auth_service import require_role
from backend.services.admin_service import (
    create_exam, update_exam, delete_exam, toggle_exam_status,
    get_exam_questions_admin, add_question, update_question, delete_question,
    get_admin_students, get_admin_results, export_results_csv,
    get_admin_dashboard_metrics
)
from backend.services.exam_service import get_all_exams

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ----------------- Dashboard -----------------

@admin_bp.route('/dashboard', methods=['GET'])
@require_role('admin')
def admin_dashboard():
    metrics = get_admin_dashboard_metrics()
    return jsonify({'success': True, 'data': metrics}), 200


# ----------------- Exams -----------------

@admin_bp.route('/exams', methods=['GET'])
@require_role('admin')
def admin_list_exams():
    from backend.database import query_db
    exams = query_db("""
        SELECT e.*, COUNT(q.id) as question_count 
        FROM exams e 
        LEFT JOIN questions q ON e.id = q.exam_id 
        GROUP BY e.id 
        ORDER BY e.created_at DESC
    """)
    return jsonify({'success': True, 'exams': exams}), 200


@admin_bp.route('/exams', methods=['POST'])
@require_role('admin')
def admin_create_exam():
    data = request.get_json() or {}
    res, status_code = create_exam(data)
    return jsonify(res), status_code


@admin_bp.route('/exams/<exam_id>', methods=['PUT'])
@require_role('admin')
def admin_update_exam(exam_id):
    data = request.get_json() or {}
    res, status_code = update_exam(exam_id, data)
    return jsonify(res), status_code


@admin_bp.route('/exams/<exam_id>', methods=['DELETE'])
@require_role('admin')
def admin_delete_exam(exam_id):
    res, status_code = delete_exam(exam_id)
    return jsonify(res), status_code


@admin_bp.route('/exams/<exam_id>/status', methods=['PATCH'])
@require_role('admin')
def admin_toggle_status(exam_id):
    data = request.get_json() or {}
    target = data.get('status')
    res, status_code = toggle_exam_status(exam_id, target)
    return jsonify(res), status_code


# ----------------- Questions -----------------

@admin_bp.route('/exams/<exam_id>/questions', methods=['GET'])
@require_role('admin')
def admin_get_questions(exam_id):
    questions = get_exam_questions_admin(exam_id)
    return jsonify({'success': True, 'questions': questions}), 200


@admin_bp.route('/exams/<exam_id>/questions', methods=['POST'])
@require_role('admin')
def admin_add_question(exam_id):
    data = request.get_json() or {}
    res, status_code = add_question(exam_id, data)
    return jsonify(res), status_code


@admin_bp.route('/questions/<int:question_id>', methods=['PUT'])
@require_role('admin')
def admin_update_question(question_id):
    data = request.get_json() or {}
    res, status_code = update_question(question_id, data)
    return jsonify(res), status_code


@admin_bp.route('/questions/<int:question_id>', methods=['DELETE'])
@require_role('admin')
def admin_delete_question(question_id):
    res, status_code = delete_question(question_id)
    return jsonify(res), status_code


# ----------------- Students -----------------

@admin_bp.route('/students', methods=['GET'])
@require_role('admin')
def admin_list_students():
    search = request.args.get('q', '').strip()
    department = request.args.get('dept', '').strip()
    students = get_admin_students(search, department)
    return jsonify({'success': True, 'students': students}), 200


# ----------------- Results & CSV Export -----------------

@admin_bp.route('/results', methods=['GET'])
@require_role('admin')
def admin_results_list():
    student = request.args.get('student', '').strip()
    exam_id = request.args.get('exam', '').strip()
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    results = get_admin_results(student, exam_id, from_date, to_date)
    return jsonify({'success': True, 'results': results}), 200


@admin_bp.route('/results/export', methods=['GET'])
@require_role('admin')
def admin_results_export_csv():
    student = request.args.get('student', '').strip()
    exam_id = request.args.get('exam', '').strip()
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    csv_data = export_results_csv(student, exam_id, from_date, to_date)
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=results.csv'}
    )
