"""
Admin Service:
Handles exam CRUD, question management, student metrics, admin results filtering, and CSV export.
"""

import io
import csv
from datetime import datetime, timezone
from backend.database import query_db, execute_db

# ----------------- Exam Management -----------------

def create_exam(data):
    exam_id = data.get('id') or data.get('code', '').lower().replace(' ', '-')
    title = (data.get('title') or '').strip()
    code = (data.get('code') or '').strip().upper()
    category = (data.get('category') or 'General').strip()
    description = (data.get('description') or '').strip()
    duration = int(data.get('duration') or 30)
    total_marks = int(data.get('total_marks') or 10)
    pass_marks = int(data.get('pass_marks') or 6)
    status = data.get('status', 'draft')
    show_answers = 1 if data.get('show_answers', True) else 0

    if not title or len(title) < 3:
        return {'success': False, 'message': 'Exam title must be at least 3 characters long.'}, 400

    if not code:
        return {'success': False, 'message': 'Course code is required.'}, 400

    existing = query_db("SELECT id FROM exams WHERE id = %s", (exam_id,), one=True)
    if existing:
        return {'success': False, 'message': f'An exam with ID "{exam_id}" already exists.'}, 409

    execute_db("""
        INSERT INTO exams (id, category, code, title, description, duration, total_marks, pass_marks, status, show_answers)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (exam_id, category, code, title, description, duration, total_marks, pass_marks, status, show_answers))

    return {'success': True, 'message': 'Exam created successfully.', 'exam_id': exam_id}, 201


def update_exam(exam_id, data):
    existing = query_db("SELECT * FROM exams WHERE id = %s", (exam_id,), one=True)
    if not existing:
        return {'success': False, 'message': 'Exam not found.'}, 404

    title = data.get('title', existing['title']).strip()
    code = data.get('code', existing['code']).strip().upper()
    category = data.get('category', existing['category']).strip()
    description = data.get('description', existing.get('description', '')).strip()
    duration = int(data.get('duration', existing['duration']))
    total_marks = int(data.get('total_marks', existing['total_marks']))
    pass_marks = int(data.get('pass_marks', existing['pass_marks']))
    status = data.get('status', existing['status'])
    show_answers = 1 if data.get('show_answers', existing['show_answers']) else 0

    execute_db("""
        UPDATE exams 
        SET title = %s, code = %s, category = %s, description = %s, duration = %s, 
            total_marks = %s, pass_marks = %s, status = %s, show_answers = %s
        WHERE id = %s
    """, (title, code, category, description, duration, total_marks, pass_marks, status, show_answers, exam_id))

    return {'success': True, 'message': 'Exam updated successfully.'}, 200


def delete_exam(exam_id):
    existing = query_db("SELECT id FROM exams WHERE id = %s", (exam_id,), one=True)
    if not existing:
        return {'success': False, 'message': 'Exam not found.'}, 404

    execute_db("DELETE FROM questions WHERE exam_id = %s", (exam_id,))
    execute_db("DELETE FROM exams WHERE id = %s", (exam_id,))
    return {'success': True, 'message': 'Exam and associated questions deleted successfully.'}, 200


def toggle_exam_status(exam_id, new_status=None):
    existing = query_db("SELECT status FROM exams WHERE id = %s", (exam_id,), one=True)
    if not existing:
        return {'success': False, 'message': 'Exam not found.'}, 404

    target_status = new_status or ('draft' if existing['status'] == 'published' else 'published')
    execute_db("UPDATE exams SET status = %s WHERE id = %s", (target_status, exam_id))
    return {'success': True, 'message': f'Exam is now {target_status}.', 'status': target_status}, 200


# ----------------- Question Management -----------------

def get_exam_questions_admin(exam_id):
    questions = query_db("""
        SELECT id, exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation
        FROM questions
        WHERE exam_id = %s
        ORDER BY id ASC
    """, (exam_id,))

    formatted = []
    for q in questions:
        formatted.append({
            'id': q['id'],
            'exam_id': q['exam_id'],
            'text': q['question_text'],
            'opts': [q['option_a'], q['option_b'], q['option_c'], q['option_d']],
            'a': q['correct_option'],
            'explanation': q['explanation']
        })
    return formatted


def add_question(exam_id, data):
    existing_exam = query_db("SELECT id FROM exams WHERE id = %s", (exam_id,), one=True)
    if not existing_exam:
        return {'success': False, 'message': 'Exam not found.'}, 404

    text = (data.get('text') or data.get('question_text') or '').strip()
    opts = data.get('opts') or [
        data.get('option_a', ''),
        data.get('option_b', ''),
        data.get('option_c', ''),
        data.get('option_d', '')
    ]
    correct = int(data.get('a') if data.get('a') is not None else data.get('correct_option', 0))
    explanation = (data.get('explanation') or '').strip()

    if len(text) < 5:
        return {'success': False, 'message': 'Please provide the question text.'}, 400

    if len(opts) < 4 or any(not str(o).strip() for o in opts[:4]):
        return {'success': False, 'message': 'All four options must be filled.'}, 400

    q_id, _ = execute_db("""
        INSERT INTO questions (exam_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (exam_id, text, opts[0], opts[1], opts[2], opts[3], correct, explanation))

    return {'success': True, 'message': 'Question added successfully.', 'question_id': q_id}, 201


def update_question(question_id, data):
    existing = query_db("SELECT * FROM questions WHERE id = %s", (question_id,), one=True)
    if not existing:
        return {'success': False, 'message': 'Question not found.'}, 404

    text = (data.get('text') or data.get('question_text') or existing['question_text']).strip()
    opts = data.get('opts') or [
        data.get('option_a', existing['option_a']),
        data.get('option_b', existing['option_b']),
        data.get('option_c', existing['option_c']),
        data.get('option_d', existing['option_d'])
    ]
    correct = int(data.get('a') if data.get('a') is not None else data.get('correct_option', existing['correct_option']))
    explanation = (data.get('explanation') or existing.get('explanation', '')).strip()

    execute_db("""
        UPDATE questions
        SET question_text = %s, option_a = %s, option_b = %s, option_c = %s, option_d = %s,
            correct_option = %s, explanation = %s
        WHERE id = %s
    """, (text, opts[0], opts[1], opts[2], opts[3], correct, explanation, question_id))

    return {'success': True, 'message': 'Question updated successfully.'}, 200


def delete_question(question_id):
    existing = query_db("SELECT id FROM questions WHERE id = %s", (question_id,), one=True)
    if not existing:
        return {'success': False, 'message': 'Question not found.'}, 404

    execute_db("DELETE FROM questions WHERE id = %s", (question_id,))
    return {'success': True, 'message': 'Question deleted successfully.'}, 200


# ----------------- Student Management -----------------

def get_admin_students(search='', department=''):
    students = query_db("""
        SELECT u.id, u.name, u.email, u.registration_number, u.department, u.created_at,
               COUNT(a.id) as attempts_count,
               AVG(a.percentage) as avg_score
        FROM users u
        LEFT JOIN exam_attempts a ON u.id = a.user_id
        WHERE u.role = 'student'
        GROUP BY u.id
        ORDER BY u.id DESC
    """)

    results = []
    for s in students:
        attempts = s.get('attempts_count', 0)
        avg = round(float(s.get('avg_score') or 0)) if attempts else 0

        # Filter
        name_match = not search or (search.lower() in (s['name'] + s['email'] + s['registration_number']).lower())
        dept_match = not department or (s['department'] == department)

        if name_match and dept_match:
            results.append({
                'id': s['registration_number'],
                'user_id': s['id'],
                'name': s['name'],
                'email': s['email'],
                'dept': s['department'],
                'attempts': attempts,
                'avg': avg,
                'active': True
            })

    return results


# ----------------- Admin Results & Reports -----------------

def get_admin_results(student_param='', exam_id='', from_date=None, to_date=None):
    query = """
        SELECT a.id, a.user_id, a.exam_id, a.score, a.total_questions, a.percentage, a.passed,
               a.time_taken, a.submitted_at,
               u.name as student_name, u.registration_number as student_reg, u.email as student_email,
               e.title as exam_title, e.code as exam_code, e.total_marks, e.pass_marks
        FROM exam_attempts a
        JOIN users u ON a.user_id = u.id
        JOIN exams e ON a.exam_id = e.id
        WHERE 1=1
    """
    params = []

    if student_param:
        query += " AND (u.registration_number = %s OR u.email = %s OR CAST(u.id AS CHAR) = %s)"
        params.extend([student_param, student_param, student_param])

    if exam_id:
        query += " AND a.exam_id = %s"
        params.append(exam_id)

    if from_date:
        query += " AND a.submitted_at >= %s"
        params.append(from_date)

    if to_date:
        query += " AND a.submitted_at <= %s"
        params.append(to_date)

    query += " ORDER BY a.submitted_at DESC"

    rows = query_db(query, tuple(params))
    results = []
    for r in rows:
        results.append({
            'id': r['id'],
            'student': r['student_name'],
            'sid': r['student_reg'],
            'email': r['student_email'],
            'examId': r['exam_id'],
            'exam_title': r['exam_title'],
            'score': r['score'],
            'marks': r['total_marks'],
            'percentage': float(r['percentage']),
            'passed': bool(r['passed']),
            'time_taken': r['time_taken'],
            'date': r['submitted_at']
        })
    return results


def export_results_csv(student_param='', exam_id='', from_date=None, to_date=None):
    results = get_admin_results(student_param, exam_id, from_date, to_date)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Student', 'Register Number', 'Email', 'Exam', 'Submitted At', 'Score', 'Total Marks', 'Percentage', 'Outcome'])

    for r in results:
        writer.writerow([
            r['student'],
            r['sid'],
            r['email'],
            r['exam_title'],
            str(r['date']),
            r['score'],
            r['marks'],
            f"{r['percentage']}%",
            'Passed' if r['passed'] else 'Failed'
        ])

    return output.getvalue()


# ----------------- Admin Dashboard -----------------

def get_admin_dashboard_metrics():
    total_students = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'student'", one=True)['c']
    all_exams = query_db("SELECT id, title, code, total_marks, pass_marks, status FROM exams")
    total_exams = len(all_exams)
    active_exams = len([e for e in all_exams if e['status'] == 'published'])

    total_attempts = query_db("SELECT COUNT(*) as c FROM exam_attempts", one=True)['c']
    avg_score_row = query_db("SELECT AVG(percentage) as avg_p FROM exam_attempts", one=True)
    overall_avg = round(float(avg_score_row['avg_p'] or 0), 1)

    # Average score by exam
    exam_stats = query_db("""
        SELECT e.id, e.title, AVG(a.percentage) as avg_p, COUNT(a.id) as attempts
        FROM exams e
        JOIN exam_attempts a ON e.id = a.exam_id
        GROUP BY e.id
    """)
    bars = []
    for s in exam_stats:
        bars.append({
            'title': s['title'].split(':')[0],
            'avg': round(float(s['avg_p'] or 0)),
            'attempts': s['attempts']
        })

    # Recent attempts
    recent_attempts = get_admin_results()[:6]

    return {
        'total_students': total_students,
        'total_exams': total_exams,
        'active_exams': active_exams,
        'total_attempts': total_attempts,
        'overall_average': overall_avg,
        'exam_averages': bars,
        'recent_attempts': recent_attempts,
        'exams': all_exams
    }
