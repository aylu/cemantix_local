const adminForm = document.getElementById('admin-form');
const targetForm = document.getElementById('target-form');
const statsEl = document.getElementById('stats');
const errorEl = document.getElementById('admin-error');
const successEl = document.getElementById('admin-success');

let lastToken = '';

function drawBarChart(canvasId, labels, values, color) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const max = Math.max(...values, 1);
  const barWidth = Math.max((canvas.width - 40) / labels.length - 10, 24);

  labels.forEach((label, i) => {
    const x = 24 + i * (barWidth + 10);
    const h = (values[i] / max) * (canvas.height - 70);
    const y = canvas.height - 40 - h;

    ctx.fillStyle = color;
    ctx.fillRect(x, y, barWidth, h);

    ctx.fillStyle = '#e5e7eb';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${values[i]}`, x + barWidth / 2, y - 8);
    ctx.fillText(label, x + barWidth / 2, canvas.height - 18);
  });
}

async function loadStats() {
  const res = await fetch(`/api/admin/stats?token=${encodeURIComponent(lastToken)}`);
  const data = await res.json();

  if (!res.ok) {
    statsEl.classList.add('hidden');
    targetForm.classList.add('hidden');
    errorEl.textContent = data.error || 'Erreur admin';
    return;
  }

  statsEl.classList.remove('hidden');
  targetForm.classList.remove('hidden');
  document.getElementById('total-guesses').textContent = data.total_guesses;
  document.getElementById('total-wins').textContent = data.total_wins;
  document.getElementById('avg-score').textContent = data.avg_score;
  document.getElementById('active-target').textContent = data.active_target;
  document.getElementById('target-source').textContent = data.target_source;

  const topPlayers = document.getElementById('top-players');
  topPlayers.innerHTML = '';
  data.top_players.forEach((p) => {
    const li = document.createElement('li');
    li.textContent = `${p.player} - ${p.attempts} essais - meilleur score ${p.best_score}`;
    topPlayers.appendChild(li);
  });

  const recent = document.getElementById('recent');
  recent.innerHTML = '';
  data.recent.forEach((r) => {
    const li = document.createElement('li');
    li.textContent = `${r.created_at} | ${r.pseudo} | ${r.guess} | ${r.score}/100${r.is_win ? ' | ✅' : ''}`;
    recent.appendChild(li);
  });

  drawBarChart(
    'score-chart',
    data.score_distribution.map((row) => row.bucket),
    data.score_distribution.map((row) => row.count),
    '#22c55e'
  );
  drawBarChart(
    'day-chart',
    data.guesses_by_day.map((row) => row.day.slice(5)),
    data.guesses_by_day.map((row) => row.count),
    '#3b82f6'
  );
}

adminForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorEl.textContent = '';
  successEl.textContent = '';

  lastToken = document.getElementById('token').value.trim();
  await loadStats();
});

targetForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorEl.textContent = '';
  successEl.textContent = '';

  const newTarget = document.getElementById('new-target').value.trim();
  const res = await fetch('/api/admin/target', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: lastToken, target: newTarget }),
  });
  const data = await res.json();

  if (!res.ok) {
    errorEl.textContent = data.error || 'Erreur admin';
    return;
  }

  successEl.textContent = '✅ Mot actif mis à jour avec succès.';
  await loadStats();
});
