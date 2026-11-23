/* Shared helpers and the page shell (sidebar, top bar, footer). */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtDate = t => {
  if (!t) return '-';
  const d = new Date(t);
  return isNaN(d) ? '-' : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
};
const fmtDateTime = t => {
  if (!t) return '-';
  const d = new Date(t);
  return isNaN(d) ? '-' : d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
};
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const badge = (txt, cls) => `<span class="badge ${cls}">${esc(txt)}</span>`;
const passBadge = (passed, exam) => {
  if (typeof passed === 'boolean') return passed ? badge('Passed', 'b-ok') : badge('Failed', 'b-bad');
  if (exam && (exam.pass !== undefined || exam.pass_marks !== undefined)) {
    const minPass = exam.pass !== undefined ? exam.pass : exam.pass_marks;
    return passed >= minPass ? badge('Passed', 'b-ok') : badge('Failed', 'b-bad');
  }
  return passed ? badge('Passed', 'b-ok') : badge('Failed', 'b-bad');
};

function toast(msg, type = '') {
  let box = $('.toast-box');
  if (!box) {
    box = document.createElement('div');
    box.className = 'toast-box';
    box.setAttribute('role', 'status');
    document.body.appendChild(box);
  }
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function withLoading(btn, ms, done) {
  const label = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Please wait';
  setTimeout(() => {
    btn.disabled = false;
    btn.innerHTML = label;
    if (done) done();
  }, ms);
}

function examCard(e) {
  const categoryBadge = e.category ? `<span class="badge b-info">${esc(e.category)}</span>` : '';
  const action = e.is_completed
    ? `<a class="btn sm sec" href="result.html?id=${e.id}">View result</a>`
    : `<a class="btn sm" href="exam-instructions.html?id=${e.id}">Start exam</a>`;

  return `<article class="exam-card">
    <div>
      <div class="ec-top">
        <h3>${esc(e.title)}</h3>
        ${categoryBadge}
        ${e.is_completed ? badge('Completed', 'b-gray') : badge('Open now', 'b-ok')}
      </div>
      <p class="hint">${esc(e.code || '')} &bull; ${e.duration} mins &bull; ${e.question_count || e.questions || 10} questions &bull; Pass mark: ${e.pass_marks || e.pass || 6}</p>
      ${e.description ? `<p class="hint" style="margin-top:4px;font-size:0.83rem;color:var(--muted)">${esc(e.description)}</p>` : ''}
    </div>
    <div>${action}</div>
  </article>`;
}

const ICON = {
  dash: '<path d="M3 3h8v8H3zM13 3h8v5h-8zM13 11h8v10h-8zM3 14h8v7H3z"/>',
  book: '<path d="M4 4h12a4 4 0 0 1 4 4v12H8a4 4 0 0 1-4-4z"/><path d="M8 4v16"/>',
  hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c.7-4.5 4-7 8-7s7.3 2.5 8 7"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-4 3.5-6 6.5-6s6 2 6.5 6M16 5a3.5 3.5 0 0 1 0 7M18 14c2 .7 3.3 2.7 3.5 6"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  out: '<path d="M9 4H5v16h4M16 8l4 4-4 4M20 12H9"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>'
};
const svg = k => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k]}</svg>`;
const NAV = {
  student: [['student-dashboard.html', 'Dashboard', 'dash'], ['exams.html', 'Available exams', 'book'], ['history.html', 'Exam history', 'hist'], ['profile.html', 'Profile and settings', 'user']],
  admin: [['admin-dashboard.html', 'Dashboard', 'dash'], ['admin-exams.html', 'Exams', 'book'], ['questions.html', 'Questions', 'help'], ['students.html', 'Students', 'users'], ['admin-results.html', 'Results', 'chart'], ['profile.html?role=admin', 'Profile and settings', 'user']]
};

function initShell() {
  const body = document.body, page = $('#page');
  const link = document.createElement('link'); link.rel = 'icon'; link.href = 'assets/favicon.svg'; document.head.appendChild(link);
  const role = new URLSearchParams(location.search).get('role') || body.dataset.role;
  const year = new Date().getFullYear();

  if (role === 'exam') return;

  if (role === 'public') {
    const h = document.createElement('header'); h.className = 'pub-h';
    h.innerHTML = `<div class="pub-in">
      <a class="brand" href="index.html"><span class="brand-mark">E</span>ExamDesk</a>
      <nav><a class="btn sec sm" href="login.html">Log in</a><a class="btn sm" href="register.html">Register</a></nav>
    </div>`;
    const f = document.createElement('footer'); f.className = 'footer';
    f.innerHTML = `<span>ExamDesk Online Examination Portal</span><span>&copy; ${year} Cloud & Systems Engineering</span>`;
    body.prepend(h); body.appendChild(f);
    return;
  }

  // Protected pages check
  const currentUser = window.API ? window.API.getUser() : null;
  const currentToken = window.API ? window.API.getToken() : null;

  if (!currentUser || !currentToken) {
    window.location.href = 'login.html';
    return;
  }

  const user = currentUser || (window.DB ? window.DB[role] : { name: 'Student', registration_number: 'N/A' });
  const navItems = NAV[role] || NAV.student;

  const items = navItems.map(([href, label, ic]) => {
    const file = location.pathname.split('/').pop(), isAdminQ = new URLSearchParams(location.search).get('role') === 'admin';
    const cur = href.split('?')[0] === file && href.includes('role=admin') === isAdminQ;
    return `<a href="${href}" ${cur ? 'aria-current="page"' : ''}>${svg(ic)}<span>${label}</span></a>`;
  }).join('');

  const regLabel = user.role === 'admin' ? 'Administrator' : `Reg: ${esc(user.registration_number || user.id || 'N/A')}`;
  const initials = (user.name || 'User').split(' ').filter(w => /^[A-Za-z]/.test(w)).slice(0, 2).map(w => w[0].toUpperCase()).join('') || 'U';

  const shell = document.createElement('div'); shell.className = 'app';
  shell.innerHTML = `<aside class="sidebar" id="sidebar" aria-label="Main navigation">
      <a class="brand" href="${role === 'admin' ? 'admin-dashboard.html' : 'student-dashboard.html'}"><span class="brand-mark">E</span><span class="brand-text">ExamDesk</span></a>
      <nav class="nav"><div class="nav-group">${role === 'admin' ? 'Administration' : 'My exams'}</div>${items}</nav>
      <div class="sb-foot nav"><a href="#" id="signOutBtn">${svg('out')}<span>Sign out</span></a></div></aside>
    <div class="scrim" id="scrim"></div>
    <div class="main"><header class="topbar">
      <button class="icon-btn" id="toggle" aria-label="Toggle sidebar" aria-controls="sidebar">${svg('menu')}</button>
      <span class="tb-title">${esc(body.dataset.title || '')}</span>
      <div class="tb-right">
        <div class="tb-name">${esc(user.name)}<small>${regLabel}</small></div>
        <span class="avatar" aria-hidden="true">${initials}</span>
      </div></header>
      <main id="main"></main>
      <footer class="footer"><span>ExamDesk Online Examination Portal</span><span>&copy; ${year} Cloud & Systems Engineering</span></footer></div>`;

  $('#main', shell).appendChild(page);
  body.prepend(shell);

  const mobile = () => matchMedia('(max-width:860px)').matches;
  if (!mobile() && localStorage.getItem('sb') === '1') shell.classList.add('collapsed');
  $('#toggle').onclick = () => {
    if (mobile()) shell.classList.toggle('open');
    else {
      shell.classList.toggle('collapsed');
      try { localStorage.setItem('sb', shell.classList.contains('collapsed') ? '1' : '0'); } catch (e) {}
    }
  };
  $('#scrim').onclick = () => shell.classList.remove('open');

  // Sign out functionality
  const signOutBtn = $('#signOutBtn', shell);
  if (signOutBtn) {
    signOutBtn.onclick = (e) => {
      e.preventDefault();
      if (window.API) window.API.logout();
      else {
        localStorage.clear();
        location.href = 'login.html';
      }
    };
  }
}

document.addEventListener('DOMContentLoaded', initShell);
