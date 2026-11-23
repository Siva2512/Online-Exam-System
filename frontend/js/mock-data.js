/* ExamDesk Data Model and Fallback Store */
const DAY = 864e5, NOW = Date.now();
const at = (days, hour = 9) => { const t = new Date(NOW + days * DAY); t.setHours(hour, 0, 0, 0); return t.getTime(); };

// Read logged in user from localStorage if present
let savedUser = null;
try { savedUser = JSON.parse(localStorage.getItem('user') || 'null'); } catch (e) {}

const DB = {
  student: savedUser || { name: 'Student User', id: 'NEW001', email: 'student@college.edu', dept: 'Computer Science', year: 'First year' },
  admin:   { name: 'Dr. R. Venkatesh', id: 'ADM001', email: 'admin@college.edu', dept: 'Examination Cell', year: 'Administrator' },
  exams: [
    {
      id: 'aws-basics',
      category: 'AWS Basics',
      code: 'AWS-101',
      title: 'AWS Basics Certification Practice Test',
      duration: 30,
      questions: 10,
      marks: 10,
      pass: 6,
      start: at(-1),
      end: at(14),
      status: 'published',
      showAnswers: true,
      attempts: 0
    },
    {
      id: 'networking-basics',
      category: 'Networking Basics',
      code: 'NET-101',
      title: 'Computer Networking Fundamentals Test',
      duration: 30,
      questions: 10,
      marks: 10,
      pass: 6,
      start: at(-1),
      end: at(14),
      status: 'published',
      showAnswers: true,
      attempts: 0
    }
  ],
  // Empty attempts by default to ensure no sample results or default scores are shown to new users
  attempts: [],
  students: [],
  results: [],
  questions: {}
};

window.DB = DB;
