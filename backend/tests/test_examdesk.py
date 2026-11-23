import unittest
import json
import os
from pathlib import Path

# Set test environment
os.environ['DB_TYPE'] = 'sqlite'
test_db_path = Path(__file__).resolve().parent / 'test_examdesk.db'
if test_db_path.exists():
    test_db_path.unlink()
os.environ['SQLITE_PATH'] = str(test_db_path)

from backend.app import create_app
from backend.database import init_db

class ExamDeskTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass

    def test_01_user_registration_and_duplicate_prevention(self):
        # 1. Register student 1
        res = self.client.post('/api/auth/register', json={
            'name': 'Priya Sharma',
            'email': 'priya.sharma@example.com',
            'registration_number': 'REG-2026-001',
            'password': 'SecurePassword123'
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('token', data)
        self.assertEqual(data['user']['registration_number'], 'REG-2026-001')

        # 2. Try registering with duplicate email
        res_dup_email = self.client.post('/api/auth/register', json={
            'name': 'Priya Other',
            'email': 'priya.sharma@example.com',
            'registration_number': 'REG-2026-999',
            'password': 'SecurePassword123'
        })
        self.assertEqual(res_dup_email.status_code, 409)
        self.assertIn('email address already exists', res_dup_email.get_json()['message'])

        # 3. Try registering with duplicate registration number
        res_dup_reg = self.client.post('/api/auth/register', json={
            'name': 'Another Student',
            'email': 'another@example.com',
            'registration_number': 'REG-2026-001',
            'password': 'SecurePassword123'
        })
        self.assertEqual(res_dup_reg.status_code, 409)
        self.assertIn('registration number is already registered', res_dup_reg.get_json()['message'])

    def test_02_login_and_token_authentication(self):
        # Successful login
        res = self.client.post('/api/auth/login', json={
            'email': 'priya.sharma@example.com',
            'password': 'SecurePassword123'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('token', data)

        # Invalid password
        res_invalid = self.client.post('/api/auth/login', json={
            'email': 'priya.sharma@example.com',
            'password': 'WrongPassword!'
        })
        self.assertEqual(res_invalid.status_code, 401)

    def test_03_new_user_sees_empty_results(self):
        # Register a brand new student
        res = self.client.post('/api/auth/register', json={
            'name': 'New Student',
            'email': 'new.student@example.com',
            'registration_number': 'NEW-REG-100',
            'password': 'Password123'
        })
        self.assertEqual(res.status_code, 201)
        token = res.get_json()['token']

        # Get results for new user: must be empty list
        headers = {'Authorization': f'Bearer {token}'}
        res_results = self.client.get('/api/results', headers=headers)
        self.assertEqual(res_results.status_code, 200)
        results = res_results.get_json()['results']
        self.assertEqual(len(results), 0, "New student must have zero results")

        # Stats for new user
        res_stats = self.client.get('/api/stats', headers=headers)
        self.assertEqual(res_stats.status_code, 200)
        stats = res_stats.get_json()['stats']
        self.assertEqual(stats['completed_exams'], 0)
        self.assertEqual(stats['average_score'], 0)

    def test_04_exam_categories_and_masked_questions(self):
        # Log in as Priya
        login_res = self.client.post('/api/auth/login', json={
            'email': 'priya.sharma@example.com',
            'password': 'SecurePassword123'
        })
        token = login_res.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # List exams
        res_exams = self.client.get('/api/exams')
        self.assertEqual(res_exams.status_code, 200)
        exams = res_exams.get_json()['exams']
        categories = [e['category'] for e in exams]
        self.assertIn('AWS Basics', categories)
        self.assertIn('Networking Basics', categories)

        # Retrieve questions for AWS Basics - verify correct answers are hidden
        res_aws_q = self.client.get('/api/exams/aws-basics/questions', headers=headers)
        self.assertEqual(res_aws_q.status_code, 200)
        q_data = res_aws_q.get_json()
        questions = q_data['questions']
        self.assertGreaterEqual(len(questions), 10)
        for q in questions:
            self.assertEqual(len(q['opts']), 4)
            self.assertNotIn('correct_option', q, "Correct option must NOT be sent to client")
            self.assertNotIn('explanation', q, "Explanation must NOT be sent to client before submission")

    def test_05_submit_aws_basics_test_and_calculate_score(self):
        login_res = self.client.post('/api/auth/login', json={
            'email': 'priya.sharma@example.com',
            'password': 'SecurePassword123'
        })
        token = login_res.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # Submit answers for AWS basics: provide 8 correct answers and 2 wrong answers
        # From seed:
        # Q1: 1 (B), Q2: 0 (A), Q3: 1 (B), Q4: 2 (C), Q5: 2 (C),
        # Q6: 0 (A), Q7: 1 (B), Q8: 1 (B), Q9: 2 (C), Q10: 1 (B)
        res_q = self.client.get('/api/exams/aws-basics/questions', headers=headers)
        questions = res_q.get_json()['questions']

        answers = {
            str(questions[0]['id']): 1, # Correct
            str(questions[1]['id']): 0, # Correct
            str(questions[2]['id']): 1, # Correct
            str(questions[3]['id']): 2, # Correct
            str(questions[4]['id']): 2, # Correct
            str(questions[5]['id']): 0, # Correct
            str(questions[6]['id']): 1, # Correct
            str(questions[7]['id']): 1, # Correct
            str(questions[8]['id']): 0, # Wrong (correct is 2)
            str(questions[9]['id']): 0  # Wrong (correct is 1)
        }

        sub_res = self.client.post('/api/exams/aws-basics/submit', headers=headers, json={
            'answers': answers,
            'time_taken': 15
        })
        self.assertEqual(sub_res.status_code, 200)
        attempt = sub_res.get_json()['attempt']
        self.assertEqual(attempt['score'], 8)
        self.assertEqual(attempt['total_questions'], 10)
        self.assertEqual(attempt['percentage'], 80.0)
        self.assertTrue(attempt['passed'])

    def test_06_networking_basics_and_isolated_results(self):
        login_res = self.client.post('/api/auth/login', json={
            'email': 'priya.sharma@example.com',
            'password': 'SecurePassword123'
        })
        token = login_res.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # At this stage, Priya has completed AWS Basics but NOT Networking Basics
        res_results = self.client.get('/api/results', headers=headers)
        results = res_results.get_json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['exam_id'], 'aws-basics')

        # Now take Networking Basics
        res_net_q = self.client.get('/api/exams/networking-basics/questions', headers=headers)
        net_questions = res_net_q.get_json()['questions']

        # Answers: answer all correctly
        # Net seed answers:
        # Q1: 1, Q2: 2, Q3: 0, Q4: 1, Q5: 1, Q6: 0, Q7: 0, Q8: 1, Q9: 0, Q10: 1
        net_answers = {
            str(net_questions[0]['id']): 1,
            str(net_questions[1]['id']): 2,
            str(net_questions[2]['id']): 0,
            str(net_questions[3]['id']): 1,
            str(net_questions[4]['id']): 1,
            str(net_questions[5]['id']): 0,
            str(net_questions[6]['id']): 0,
            str(net_questions[7]['id']): 1,
            str(net_questions[8]['id']): 0,
            str(net_questions[9]['id']): 1
        }

        sub_res = self.client.post('/api/exams/networking-basics/submit', headers=headers, json={
            'answers': net_answers,
            'time_taken': 18
        })
        self.assertEqual(sub_res.status_code, 200)
        attempt = sub_res.get_json()['attempt']
        self.assertEqual(attempt['score'], 10)
        self.assertEqual(attempt['percentage'], 100.0)
        self.assertTrue(attempt['passed'])

        # Now Priya should have both results
        res_results2 = self.client.get('/api/results', headers=headers)
        results2 = res_results2.get_json()['results']
        self.assertEqual(len(results2), 2)

    def test_07_authorization_cross_account_protection(self):
        # Register Student 2: Rahul
        res2 = self.client.post('/api/auth/register', json={
            'name': 'Rahul Verma',
            'email': 'rahul.verma@example.com',
            'registration_number': 'REG-2026-002',
            'password': 'Password456'
        })
        token_rahul = res2.get_json()['token']
        headers_rahul = {'Authorization': f'Bearer {token_rahul}'}

        # Rahul checks results: must be 0
        res_rahul_results = self.client.get('/api/results', headers=headers_rahul)
        self.assertEqual(len(res_rahul_results.get_json()['results']), 0)

        # Rahul tries to access Priya's attempt by ID (attempt ID 1)
        res_forbidden = self.client.get('/api/results/1', headers=headers_rahul)
        self.assertEqual(res_forbidden.status_code, 404, "Student cannot access another student's attempt")

if __name__ == '__main__':
    unittest.main()
