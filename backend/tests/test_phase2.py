import unittest
import json
import os
from pathlib import Path

# Setup test environment
os.environ['DB_TYPE'] = 'sqlite'
phase2_test_db = Path(__file__).resolve().parent / 'test_phase2.db'
if phase2_test_db.exists():
    phase2_test_db.unlink()
os.environ['SQLITE_PATH'] = str(phase2_test_db)

from backend.app import create_app

class Phase2FullTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if phase2_test_db.exists():
            try:
                phase2_test_db.unlink()
            except Exception:
                pass

    def test_01_role_based_access_control(self):
        # 1. Login as default Admin
        admin_login = self.client.post('/api/auth/login', json={
            'email': 'admin@college.edu',
            'password': 'Admin@123'
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.get_json()['token']
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        # 2. Register and login as Student
        std_reg = self.client.post('/api/auth/register', json={
            'name': 'Kavya Nair',
            'email': 'kavya.nair@college.edu',
            'registration_number': 'REG-PHASE2-01',
            'password': 'StudentPassword123'
        })
        self.assertEqual(std_reg.status_code, 201)
        student_token = std_reg.get_json()['token']
        student_headers = {'Authorization': f'Bearer {student_token}'}

        # 3. Student tries to access Admin Dashboard -> Must be 403 Forbidden
        res_forbidden = self.client.get('/api/admin/dashboard', headers=student_headers)
        self.assertEqual(res_forbidden.status_code, 403)
        self.assertIn('Access denied', res_forbidden.get_json()['message'])

        # 4. Admin accesses Admin Dashboard -> Must be 200 OK
        res_ok = self.client.get('/api/admin/dashboard', headers=admin_headers)
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.get_json()['data']
        self.assertIn('total_students', data)
        self.assertIn('total_exams', data)

    def test_02_admin_exam_and_question_crud(self):
        # Login as Admin
        admin_login = self.client.post('/api/auth/login', json={
            'email': 'admin@college.edu',
            'password': 'Admin@123'
        })
        admin_token = admin_login.get_json()['token']
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        # 1. Create a new Exam
        create_res = self.client.post('/api/admin/exams', headers=admin_headers, json={
            'id': 'docker-k8s-basics',
            'title': 'Containers and Kubernetes Architecture',
            'code': 'CS450',
            'category': 'DevOps',
            'description': 'Container runtimes, Pods, Services, and Ingress controllers.',
            'duration': 25,
            'total_marks': 5,
            'pass_marks': 3,
            'status': 'draft',
            'show_answers': True
        })
        self.assertEqual(create_res.status_code, 201)
        exam_id = create_res.get_json()['exam_id']

        # 2. Add Questions to the Exam
        q1_res = self.client.post(f'/api/admin/exams/{exam_id}/questions', headers=admin_headers, json={
            'text': 'What is the smallest deployable compute unit in a Kubernetes cluster?',
            'opts': ['Node', 'Container', 'Pod', 'Namespace'],
            'a': 2,
            'explanation': 'A Pod is the smallest execution unit in Kubernetes containing one or more containers.'
        })
        self.assertEqual(q1_res.status_code, 201)
        q1_id = q1_res.get_json()['question_id']

        # 3. View questions as Admin (verify answer keys are visible to admin)
        q_admin = self.client.get(f'/api/admin/exams/{exam_id}/questions', headers=admin_headers)
        self.assertEqual(q_admin.status_code, 200)
        q_list = q_admin.get_json()['questions']
        self.assertEqual(len(q_list), 1)
        self.assertEqual(q_list[0]['a'], 2)
        self.assertIn('Pod is the smallest', q_list[0]['explanation'])

        # 4. Toggle Exam status to Published
        toggle_res = self.client.patch(f'/api/admin/exams/{exam_id}/status', headers=admin_headers, json={'status': 'published'})
        self.assertEqual(toggle_res.status_code, 200)
        self.assertEqual(toggle_res.get_json()['status'], 'published')

        # 5. Check as Student: verify student gets questions WITHOUT answer keys
        std_login = self.client.post('/api/auth/login', json={
            'email': 'kavya.nair@college.edu',
            'password': 'StudentPassword123'
        })
        std_headers = {'Authorization': f'Bearer {std_login.get_json()["token"]}'}

        std_q = self.client.get(f'/api/exams/{exam_id}/questions', headers=std_headers)
        self.assertEqual(std_q.status_code, 200)
        student_qs = std_q.get_json()['questions']
        self.assertNotIn('a', student_qs[0])
        self.assertNotIn('correct_option', student_qs[0])
        self.assertNotIn('explanation', student_qs[0])

        # 6. Delete Question and Exam
        del_q = self.client.delete(f'/api/admin/questions/{q1_id}', headers=admin_headers)
        self.assertEqual(del_q.status_code, 200)

        del_ex = self.client.delete(f'/api/admin/exams/{exam_id}', headers=admin_headers)
        self.assertEqual(del_ex.status_code, 200)

    def test_03_student_history_isolation_and_admin_reports(self):
        # Student 1: Kavya
        kavya_login = self.client.post('/api/auth/login', json={
            'email': 'kavya.nair@college.edu',
            'password': 'StudentPassword123'
        })
        kavya_headers = {'Authorization': f'Bearer {kavya_login.get_json()["token"]}'}

        # Student 2: Vikram
        vikram_reg = self.client.post('/api/auth/register', json={
            'name': 'Vikram Seth',
            'email': 'vikram.seth@college.edu',
            'registration_number': 'REG-PHASE2-02',
            'password': 'VikramPassword123'
        })
        vikram_token = vikram_reg.get_json()['token']
        vikram_headers = {'Authorization': f'Bearer {vikram_token}'}

        # Vikram checks results -> Empty
        vikram_res0 = self.client.get('/api/results', headers=vikram_headers)
        self.assertEqual(len(vikram_res0.get_json()['results']), 0)

        # Kavya submits AWS Basics
        aws_q = self.client.get('/api/exams/aws-basics/questions', headers=kavya_headers).get_json()['questions']
        answers = {str(q['id']): 1 for q in aws_q}
        sub_res = self.client.post('/api/exams/aws-basics/submit', headers=kavya_headers, json={'answers': answers, 'time_taken': 10})
        self.assertEqual(sub_res.status_code, 200)
        kavya_att_id = sub_res.get_json()['attempt']['id']

        # Kavya sees 1 result
        kavya_res = self.client.get('/api/results', headers=kavya_headers)
        self.assertEqual(len(kavya_res.get_json()['results']), 1)

        # Vikram STILL sees 0 results (strict isolation)
        vikram_res1 = self.client.get('/api/results', headers=vikram_headers)
        self.assertEqual(len(vikram_res1.get_json()['results']), 0)

        # Vikram tries to access Kavya's attempt by ID -> 404 Not Found
        vikram_steal = self.client.get(f'/api/results/{kavya_att_id}', headers=vikram_headers)
        self.assertEqual(vikram_steal.status_code, 404)

        # Admin logs in and views All Results & CSV export
        admin_login = self.client.post('/api/auth/login', json={'email': 'admin@college.edu', 'password': 'Admin@123'})
        admin_headers = {'Authorization': f'Bearer {admin_login.get_json()["token"]}'}

        admin_results = self.client.get('/api/admin/results', headers=admin_headers)
        self.assertEqual(admin_results.status_code, 200)
        self.assertGreaterEqual(len(admin_results.get_json()['results']), 1)

        # Admin exports CSV
        csv_res = self.client.get('/api/admin/results/export', headers=admin_headers)
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(csv_res.content_type, 'text/csv; charset=utf-8')
        csv_text = csv_res.data.decode('utf-8')
        self.assertIn('Kavya Nair', csv_text)
        self.assertIn('REG-PHASE2-01', csv_text)

if __name__ == '__main__':
    unittest.main()
