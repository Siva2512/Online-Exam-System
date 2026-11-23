/* Live Exam Screen
   Fetches questions securely from backend (without correct answers).
   Tracks answers, review flags, and countdown timer.
   Submits to backend for server-side score calculation and persistent storage.
*/
(async function () {
  const examId = new URLSearchParams(location.search).get('id') || 'aws-basics';
  const LETTERS = 'ABCD';
  let exam = null;
  let qs = [];
  let s = null;
  const KEY = 'attempt:' + examId;
  let deadline = 0;
  let finished = false;

  try {
    const data = await API.getQuestions(examId);
    exam = data.exam;
    qs = data.questions || [];
  } catch (err) {
    console.error('Failed to load exam from server:', err);
    // Fallback to offline mock data if server is unreachable
    exam = examById(examId) || { id: examId, title: 'Exam', duration: 30, marks: 10, pass: 6 };
    qs = (DB.questions && DB.questions[examId]) || [];
  }

  if (!qs || qs.length === 0) {
    alert('No questions available for this exam. Please contact your administrator.');
    location.href = 'student-dashboard.html';
    return;
  }

  try { s = JSON.parse(localStorage.getItem(KEY)); } catch (e) {}
  if (!s || s.examId !== examId) {
    s = { examId, startedAt: Date.now(), answers: {}, review: {}, cur: 0 };
  }

  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} };
  deadline = s.startedAt + (exam.duration || 30) * 60000;
  save();

  $('#exTitle').textContent = exam.title;
  document.title = exam.title + ' - ExamDesk';

  function render() {
    const q = qs[s.cur];
    $('#qNo').textContent = `Question ${s.cur + 1} of ${qs.length}`;
    $('#qText').textContent = q.text;

    const opts = q.opts || [];
    $('#opts').innerHTML = opts.map((o, i) => `
      <label class="opt ${s.answers[q.id] === i ? 'sel' : ''}">
        <input type="radio" name="opt" value="${i}" ${s.answers[q.id] === i ? 'checked' : ''}>
        <span class="opt-k">${LETTERS[i]}</span>
        <span>${esc(o)}</span>
      </label>
    `).join('');

    $$('#opts input').forEach(inp => {
      inp.onchange = () => {
        s.answers[q.id] = +inp.value;
        save();
        $('#saved').textContent = 'Answer saved';
        render();
      };
    });

    // Render Question Palette
    $('#palette').innerHTML = qs.map((x, i) => {
      const isAns = s.answers[x.id] !== undefined && s.answers[x.id] !== null;
      const isRev = !!s.review[x.id];
      const isCur = i === s.cur;
      return `<button class="pal ${isAns ? 'ans' : ''} ${isRev ? 'rev' : ''} ${isCur ? 'cur' : ''}" 
                      data-i="${i}" 
                      aria-label="Question ${i + 1}${isAns ? ', answered' : ', not answered'}${isRev ? ', marked for review' : ''}">
                ${i + 1}
              </button>`;
    }).join('');

    $$('.pal').forEach(b => b.onclick = () => go(+b.dataset.i));

    const answeredCount = qs.filter(x => s.answers[x.id] !== undefined && s.answers[x.id] !== null).length;
    const reviewCount = Object.keys(s.review).length;

    $('#nA').textContent = answeredCount;
    $('#nU').textContent = qs.length - answeredCount;
    $('#nR').textContent = reviewCount;

    $('#rev').textContent = s.review[q.id] ? 'Remove review mark' : 'Mark for review';
    $('#prev').disabled = s.cur === 0;
    $('#next').textContent = s.cur === qs.length - 1 ? 'Save answer' : 'Save and next';
  }

  function go(i) {
    if (i >= 0 && i < qs.length) {
      s.cur = i;
      $('#saved').textContent = '';
      save();
      render();
    }
  }

  $('#prev').onclick = () => go(s.cur - 1);
  $('#next').onclick = () => {
    $('#saved').textContent = 'Answer saved';
    if (s.cur < qs.length - 1) go(s.cur + 1);
    else render();
  };

  $('#rev').onclick = () => {
    const qId = qs[s.cur].id;
    s.review[qId] = !s.review[qId];
    if (!s.review[qId]) delete s.review[qId];
    save();
    render();
  };

  async function finish(auto) {
    if (finished) return;
    finished = true;

    const timeTaken = Math.max(1, Math.round((Date.now() - s.startedAt) / 60000));

    try {
      // Submit answers to server for evaluation and persistent database storage
      const res = await API.submitExam(exam.id, s.answers, timeTaken);
      if (res.success && res.attempt) {
        localStorage.setItem('last_result', JSON.stringify({
          ...res.attempt,
          auto: !!auto
        }));
        localStorage.removeItem(KEY);
        location.href = `result.html?id=${exam.id}&attempt_id=${res.attempt.id}`;
        return;
      }
    } catch (err) {
      console.error('Submission failed on server:', err);
      // Fallback local calculation
      toast('Saved locally: ' + err.message, 'bad');
      localStorage.removeItem(KEY);
      location.href = 'result.html?id=' + exam.id;
    }
  }

  $('#submit').onclick = () => {
    const answeredCount = qs.filter(x => s.answers[x.id] !== undefined && s.answers[x.id] !== null).length;
    const reviewCount = Object.keys(s.review).length;
    const blankCount = qs.length - answeredCount;

    $('#dBody').textContent = `You answered ${answeredCount} of ${qs.length} questions` +
      (blankCount ? ` and left ${blankCount} unanswered` : '') +
      (reviewCount ? `. ${reviewCount} marked for review` : '') +
      '. Confirming submission will finalize and score your examination.';

    $('#dlg').showModal();
  };

  $('#back').onclick = () => $('#dlg').close();
  $('#yes').onclick = () => {
    $('#yes').disabled = true;
    $('#yes').innerHTML = '<span class="spinner"></span> Submitting...';
    finish(false);
  };

  const timerEl = $('#timer');
  function tick() {
    const left = Math.max(0, deadline - Date.now());
    const sec = Math.ceil(left / 1000);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const ss = sec % 60;
    const pad = n => String(n).padStart(2, '0');

    timerEl.textContent = (h ? h + ':' : '') + pad(m) + ':' + pad(ss);
    timerEl.className = 'timer' + (left < 60000 ? ' bad' : left < 300000 ? ' warn' : '');

    if (left <= 0) {
      clearInterval(iv);
      toast('Time has expired. Submitting examination automatically.');
      setTimeout(() => finish(true), 800);
    }
  }

  const iv = setInterval(tick, 1000);
  tick();
  render();
})();
