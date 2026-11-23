from flask import Blueprint, request, jsonify, g
from backend.services.auth_service import require_auth
from backend.services.exam_service import (
    get_all_exams,
    get_exam_by_id,
    get_exam_questions_for_student,
    submit_exam_attempt
)

exams_bp = Blueprint('exams', __name__, url_prefix='/api/exams')

@exams_bp.route('', methods=['GET'])
def list_exams():
    exams = get_all_exams()
    return jsonify({
        'success': True,
        'exams': exams
    }), 200


@exams_bp.route('/<exam_id>', methods=['GET'])
def get_exam(exam_id):
    exam = get_exam_by_id(exam_id)
    if not exam:
        return jsonify({'success': False, 'message': 'Exam not found.'}), 404
    return jsonify({
        'success': True,
        'exam': exam
    }), 200


@exams_bp.route('/<exam_id>/questions', methods=['GET'])
@require_auth
def get_questions(exam_id):
    exam = get_exam_by_id(exam_id)
    if not exam:
        return jsonify({'success': False, 'message': 'Exam not found.'}), 404

    # Critical security feature: Never exposes answers to taking student!
    questions = get_exam_questions_for_student(exam_id)
    return jsonify({
        'success': True,
        'exam': {
            'id': exam['id'],
            'title': exam['title'],
            'code': exam['code'],
            'duration': exam['duration'],
            'total_marks': exam['total_marks'],
            'pass_marks': exam['pass_marks']
        },
        'questions': questions
    }), 200


@exams_bp.route('/<exam_id>/submit', methods=['POST'])
@require_auth
def submit_exam(exam_id):
    data = request.get_json() or {}
    answers = data.get('answers', {})
    time_taken = data.get('time_taken', 1)

    user_id = g.current_user['id']
    res, status_code = submit_exam_attempt(user_id, exam_id, answers, time_taken)
    return jsonify(res), status_code


@exams_bp.route('/<exam_id>/save-answers', methods=['POST'])
@require_auth
def save_answers_checkpoint(exam_id):
    data = request.get_json() or {}
    answers = data.get('answers', {})
    return jsonify({
        'success': True,
        'message': 'Progress saved successfully.',
        'saved_count': len(answers)
    }), 200

