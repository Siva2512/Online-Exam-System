"""
Data models and dictionary serializers for ExamDesk entities:
User, Exam, Question, and ExamAttempt.
"""

import json
from datetime import datetime, timezone

class User:
    def __init__(self, id=None, name='', email='', registration_number='', password_hash='', role='student', department='Computer Science', created_at=None):
        self.id = id
        self.name = name
        self.email = email
        self.registration_number = registration_number
        self.password_hash = password_hash
        self.role = role
        self.department = department
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row.get('id'),
            name=row.get('name'),
            email=row.get('email'),
            registration_number=row.get('registration_number'),
            password_hash=row.get('password_hash'),
            role=row.get('role', 'student'),
            department=row.get('department', 'Computer Science'),
            created_at=row.get('created_at')
        )

    def to_dict(self, include_sensitive=False):
        d = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'registration_number': self.registration_number,
            'role': self.role,
            'department': self.department,
            'created_at': str(self.created_at) if self.created_at else None
        }
        if include_sensitive:
            d['password_hash'] = self.password_hash
        return d


class Exam:
    def __init__(self, id, category, code, title, description='', duration=30, total_marks=10, pass_marks=6, status='published', show_answers=True, created_at=None, question_count=0):
        self.id = id
        self.category = category
        self.code = code
        self.title = title
        self.description = description
        self.duration = duration
        self.total_marks = total_marks
        self.pass_marks = pass_marks
        self.status = status
        self.show_answers = bool(show_answers)
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.question_count = question_count

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row.get('id'),
            category=row.get('category', 'General'),
            code=row.get('code', ''),
            title=row.get('title', ''),
            description=row.get('description', ''),
            duration=row.get('duration', 30),
            total_marks=row.get('total_marks', 10),
            pass_marks=row.get('pass_marks', 6),
            status=row.get('status', 'published'),
            show_answers=bool(row.get('show_answers', 1)),
            created_at=row.get('created_at'),
            question_count=row.get('question_count', 0)
        )

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'code': self.code,
            'title': self.title,
            'description': self.description,
            'duration': self.duration,
            'total_marks': self.total_marks,
            'pass_marks': self.pass_marks,
            'status': self.status,
            'show_answers': self.show_answers,
            'question_count': self.question_count,
            'created_at': str(self.created_at) if self.created_at else None
        }


class Question:
    def __init__(self, id, exam_id, question_text, option_a, option_b, option_c, option_d, correct_option=0, explanation='', created_at=None):
        self.id = id
        self.exam_id = exam_id
        self.question_text = question_text
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.correct_option = correct_option
        self.explanation = explanation
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row.get('id'),
            exam_id=row.get('exam_id'),
            question_text=row.get('question_text'),
            option_a=row.get('option_a'),
            option_b=row.get('option_b'),
            option_c=row.get('option_c'),
            option_d=row.get('option_d'),
            correct_option=row.get('correct_option', 0),
            explanation=row.get('explanation', ''),
            created_at=row.get('created_at')
        )

    def to_dict(self, include_answer=False):
        """
        When student takes the test, include_answer must be FALSE.
        Admin view or post-submission review may include_answer = TRUE.
        """
        d = {
            'id': self.id,
            'exam_id': self.exam_id,
            'text': self.question_text,
            'opts': [self.option_a, self.option_b, self.option_c, self.option_d]
        }
        if include_answer:
            d['a'] = self.correct_option
            d['explanation'] = self.explanation
        return d


class ExamAttempt:
    def __init__(self, id, user_id, exam_id, score, total_questions, percentage, passed, time_taken, answers_json=None, submitted_at=None):
        self.id = id
        self.user_id = user_id
        self.exam_id = exam_id
        self.score = score
        self.total_questions = total_questions
        self.percentage = float(percentage)
        self.passed = bool(passed)
        self.time_taken = time_taken
        self.answers_json = answers_json or '{}'
        self.submitted_at = submitted_at or datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            id=row.get('id'),
            user_id=row.get('user_id'),
            exam_id=row.get('exam_id'),
            score=row.get('score', 0),
            total_questions=row.get('total_questions', 0),
            percentage=row.get('percentage', 0.0),
            passed=bool(row.get('passed', 0)),
            time_taken=row.get('time_taken', 1),
            answers_json=row.get('answers_json', '{}'),
            submitted_at=row.get('submitted_at')
        )

    def to_dict(self):
        answers = {}
        try:
            answers = json.loads(self.answers_json)
        except Exception:
            pass

        return {
            'id': self.id,
            'user_id': self.user_id,
            'exam_id': self.exam_id,
            'score': self.score,
            'total_questions': self.total_questions,
            'percentage': self.percentage,
            'passed': self.passed,
            'time_taken': self.time_taken,
            'answers': answers,
            'submitted_at': str(self.submitted_at) if self.submitted_at else None
        }
