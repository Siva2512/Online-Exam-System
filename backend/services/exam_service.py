import json
from datetime import datetime, timezone
from backend.database import query_db, execute_db

def get_all_exams():
    """Returns all available exams with total questions count."""
    exams = query_db("""
        SELECT e.*, COUNT(q.id) as question_count 
        FROM exams e 
        LEFT JOIN questions q ON e.id = q.exam_id 
        WHERE e.status = 'published'
        GROUP BY e.id
        ORDER BY e.created_at ASC
    """)
    return exams


def get_exam_by_id(exam_id):
    """Returns details for a single exam."""
    exam = query_db("SELECT * FROM exams WHERE id = %s", (exam_id,), one=True)
    if exam:
        q_count = query_db("SELECT COUNT(*) as c FROM questions WHERE exam_id = %s", (exam_id,), one=True)
        exam['question_count'] = q_count['c'] if q_count else 0
    return exam


def get_exam_questions_for_student(exam_id):
    """
    Returns questions for an exam for taking the test.
    CRITICAL: Never exposes correct_option or explanation to the client!
    """
    rows = query_db("""
        SELECT id, exam_id, question_text, option_a, option_b, option_c, option_d 
        FROM questions 
        WHERE exam_id = %s 
        ORDER BY id ASC
    """, (exam_id,))

    questions = []
    for r in rows:
        questions.append({
            'id': r['id'],
            'exam_id': r['exam_id'],
            'text': r['question_text'],
            'opts': [r['option_a'], r['option_b'], r['option_c'], r['option_d']]
        })
    return questions


def submit_exam_attempt(user_id, exam_id, answers, time_taken):
    """
    Evaluates student answers on the server side using the database answer key.
    Calculates score, percentage, and pass/fail status and persists in RDS/DB.
    """
    exam = query_db("SELECT * FROM exams WHERE id = %s", (exam_id,), one=True)
    if not exam:
        return {'success': False, 'message': 'Exam not found.'}, 404

    # Fetch questions with correct answers from DB
    questions = query_db("""
        SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation 
        FROM questions 
        WHERE exam_id = %s 
        ORDER BY id ASC
    """, (exam_id,))

    if not questions:
        return {'success': False, 'message': 'No questions found for this exam.'}, 400

    total_questions = len(questions)
    correct_count = 0
    blank_count = 0
    incorrect_count = 0
    review_details = []

    # Format answers: dict mapping string question id to chosen option index (0, 1, 2, or 3)
    answers_map = {}
    if isinstance(answers, dict):
        answers_map = {str(k): int(v) if v is not None and v != '' else None for k, v in answers.items()}

    for idx, q in enumerate(questions):
        q_id_str = str(q['id'])
        user_choice = answers_map.get(q_id_str)
        is_correct = False
        is_blank = (user_choice is None or user_choice < 0)

        if is_blank:
            blank_count += 1
        elif user_choice == q['correct_option']:
            correct_count += 1
            is_correct = True
        else:
            incorrect_count += 1

        options = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
        review_details.append({
            'number': idx + 1,
            'id': q['id'],
            'question': q['question_text'],
            'options': options,
            'user_choice': user_choice,
            'user_choice_text': options[user_choice] if user_choice is not None and 0 <= user_choice < 4 else None,
            'correct_option': q['correct_option'] if exam['show_answers'] else None,
            'correct_option_text': options[q['correct_option']] if exam['show_answers'] else None,
            'is_correct': is_correct,
            'is_blank': is_blank,
            'explanation': q['explanation'] if exam['show_answers'] else None
        })

    # Marks calculation: default 1 mark per question
    score = correct_count
    percentage = round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
    passed = 1 if score >= exam['pass_marks'] else 0
    time_taken_min = max(1, min(exam['duration'], int(time_taken or 1)))

    answers_json_str = json.dumps(answers_map)

    # Insert attempt record
    attempt_id, _ = execute_db("""
        INSERT INTO exam_attempts (user_id, exam_id, score, total_questions, percentage, passed, time_taken, answers_json) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, exam_id, score, total_questions, percentage, passed, time_taken_min, answers_json_str))

    return {
        'success': True,
        'message': 'Exam submitted successfully.',
        'attempt': {
            'id': attempt_id,
            'exam_id': exam_id,
            'exam_title': exam['title'],
            'exam_code': exam['code'],
            'score': score,
            'total_questions': total_questions,
            'total_marks': exam['total_marks'],
            'pass_marks': exam['pass_marks'],
            'percentage': percentage,
            'passed': bool(passed),
            'time_taken': time_taken_min,
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'blank_count': blank_count,
            'show_answers': bool(exam['show_answers']),
            'review': review_details
        }
    }, 200


def get_student_attempts(user_id):
    """
    Returns only the attempts belonging to the authenticated student.
    Guarantees no leakage between users.
    """
    attempts = query_db("""
        SELECT a.id, a.user_id, a.exam_id, a.score, a.total_questions, a.percentage, a.passed, 
               a.time_taken, a.submitted_at, 
               e.title as exam_title, e.code as exam_code, e.category as exam_category, 
               e.total_marks, e.pass_marks, e.duration
        FROM exam_attempts a
        JOIN exams e ON a.exam_id = e.id
        WHERE a.user_id = %s
        ORDER BY a.submitted_at DESC, a.id DESC
    """, (user_id,))
    return attempts


def get_student_attempt_detail(user_id, attempt_id_or_exam_id):
    """
    Returns detailed attempt results including question reviews.
    Verifies that the attempt belongs to user_id.
    """
    attempt = query_db("""
        SELECT a.*, e.title as exam_title, e.code as exam_code, e.category as exam_category, 
               e.total_marks, e.pass_marks, e.duration, e.show_answers
        FROM exam_attempts a
        JOIN exams e ON a.exam_id = e.id
        WHERE a.user_id = %s AND (a.id = %s OR a.exam_id = %s)
        ORDER BY a.submitted_at DESC
        LIMIT 1
    """, (user_id, attempt_id_or_exam_id, attempt_id_or_exam_id), one=True)

    if not attempt:
        return None

    # Reconstruct question review details
    exam_id = attempt['exam_id']
    questions = query_db("""
        SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation 
        FROM questions 
        WHERE exam_id = %s 
        ORDER BY id ASC
    """, (exam_id,))

    answers_map = {}
    if attempt.get('answers_json'):
        try:
            answers_map = json.loads(attempt['answers_json'])
        except Exception:
            answers_map = {}

    correct_count = 0
    blank_count = 0
    incorrect_count = 0
    review_details = []

    for idx, q in enumerate(questions):
        q_id_str = str(q['id'])
        user_choice = answers_map.get(q_id_str)
        is_correct = False
        is_blank = (user_choice is None or user_choice < 0)

        if is_blank:
            blank_count += 1
        elif user_choice == q['correct_option']:
            correct_count += 1
            is_correct = True
        else:
            incorrect_count += 1

        options = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
        review_details.append({
            'number': idx + 1,
            'id': q['id'],
            'question': q['question_text'],
            'options': options,
            'user_choice': user_choice,
            'user_choice_text': options[user_choice] if user_choice is not None and 0 <= user_choice < 4 else None,
            'correct_option': q['correct_option'] if attempt['show_answers'] else None,
            'correct_option_text': options[q['correct_option']] if attempt['show_answers'] else None,
            'is_correct': is_correct,
            'is_blank': is_blank,
            'explanation': q['explanation'] if attempt['show_answers'] else None
        })

    attempt['correct_count'] = correct_count
    attempt['incorrect_count'] = incorrect_count
    attempt['blank_count'] = blank_count
    attempt['passed'] = bool(attempt['passed'])
    attempt['show_answers'] = bool(attempt['show_answers'])
    attempt['review'] = review_details
    return attempt


def get_student_dashboard_data(user_id):
    """
    Returns student dashboard metrics:
    - Available exams
    - Total completed exams
    - Recent exam attempts
    - Average score (returns 0% cleanly if no attempts)
    """
    all_exams = get_all_exams()
    student_attempts = get_student_attempts(user_id)

    completed_exam_ids = {a['exam_id'] for a in student_attempts}

    # Count completed
    completed_count = len(student_attempts)

    # Average score
    if completed_count > 0:
        total_pct = sum(float(a['percentage']) for a in student_attempts)
        avg_score = round(total_pct / completed_count)
    else:
        avg_score = 0

    # Mark completion status on exam objects
    exams_with_status = []
    for ex in all_exams:
        ex_copy = dict(ex)
        ex_copy['is_completed'] = ex['id'] in completed_exam_ids
        exams_with_status.append(ex_copy)

    return {
        'total_exams': len(all_exams),
        'completed_exams': completed_count,
        'average_score': avg_score,
        'exams': exams_with_status,
        'recent_attempts': student_attempts[:5]
    }
