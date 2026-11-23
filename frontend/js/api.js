/**
 * ExamDesk API Client
 * Seamlessly interfaces with the Flask REST Backend.
 * Automatically handles JWT Bearer tokens and error responses.
 */

const API_BASE = (window.location.port === '8000' || window.location.protocol === 'file:')
  ? 'http://127.0.0.1:5000/api'
  : '/api';

const API = {
  getToken() {
    try {
      return localStorage.getItem('auth_token');
    } catch (e) {
      return null;
    }
  },

  setToken(token) {
    try {
      localStorage.setItem('auth_token', token);
    } catch (e) {}
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem('user') || 'null');
    } catch (e) {
      return null;
    }
  },

  setUser(user) {
    try {
      localStorage.setItem('user', JSON.stringify(user));
    } catch (e) {}
  },

  clearAuth() {
    try {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      localStorage.removeItem('last_result');
    } catch (e) {}
  },

  logout() {
    this.clearAuth();
    window.location.href = 'login.html';
  },

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      });

      const data = await response.json().catch(() => ({}));

      if (response.status === 401) {
        // Protected page redirection on expired token
        const publicPages = ['login.html', 'register.html', 'index.html', '404.html', 'error.html'];
        const currentFile = window.location.pathname.split('/').pop() || 'index.html';
        if (!publicPages.includes(currentFile)) {
          this.clearAuth();
          window.location.href = 'login.html';
        }
      }

      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }

      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth Endpoints
  async register(name, email, registration_number, password, department = 'Computer Science') {
    const res = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, registration_number, password, department })
    });
    if (res.token && res.user) {
      this.setToken(res.token);
      this.setUser(res.user);
    }
    return res;
  },

  async login(email, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    if (res.token && res.user) {
      this.setToken(res.token);
      this.setUser(res.user);
    }
    return res;
  },

  async getMe() {
    return this.request('/auth/me');
  },

  // Exams Endpoints
  async getExams() {
    return this.request('/exams');
  },

  async getExam(id) {
    return this.request(`/exams/${id}`);
  },

  async getQuestions(id) {
    return this.request(`/exams/${id}/questions`);
  },

  async submitExam(id, answers, time_taken) {
    return this.request(`/exams/${id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers, time_taken })
    });
  },

  // Results & History Endpoints
  async getResults() {
    return this.request('/results');
  },

  async getResult(id) {
    return this.request(`/results/${id}`);
  },

  async getResultByExam(examId) {
    return this.request(`/results/exam/${examId}`);
  },

  async getStats() {
    return this.request('/stats');
  },

  // Admin Endpoints
  async getAdminDashboard() {
    return this.request('/admin/dashboard');
  },

  async getAdminExams() {
    return this.request('/admin/exams');
  },

  async createExam(data) {
    return this.request('/admin/exams', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async updateExam(id, data) {
    return this.request(`/admin/exams/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async deleteExam(id) {
    return this.request(`/admin/exams/${id}`, {
      method: 'DELETE'
    });
  },

  async toggleExamStatus(id, status) {
    return this.request(`/admin/exams/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
  },

  async getAdminQuestions(examId) {
    return this.request(`/admin/exams/${examId}/questions`);
  },

  async addQuestion(examId, data) {
    return this.request(`/admin/exams/${examId}/questions`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  },

  async updateQuestion(id, data) {
    return this.request(`/admin/questions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async deleteQuestion(id) {
    return this.request(`/admin/questions/${id}`, {
      method: 'DELETE'
    });
  },

  async getAdminStudents(q = '', dept = '') {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (dept) params.set('dept', dept);
    return this.request(`/admin/students?${params.toString()}`);
  },

  async getAdminResults(filters = {}) {
    const params = new URLSearchParams();
    if (filters.student) params.set('student', filters.student);
    if (filters.exam) params.set('exam', filters.exam);
    if (filters.from) params.set('from', filters.from);
    if (filters.to) params.set('to', filters.to);
    return this.request(`/admin/results?${params.toString()}`);
  },

  getAdminResultsExportUrl(filters = {}) {
    const params = new URLSearchParams();
    if (filters.student) params.set('student', filters.student);
    if (filters.exam) params.set('exam', filters.exam);
    if (filters.from) params.set('from', filters.from);
    if (filters.to) params.set('to', filters.to);
    const token = this.getToken();
    if (token) params.set('token', token);
    return `${API_BASE}/admin/results/export?${params.toString()}`;
  }
};

window.API = API;

