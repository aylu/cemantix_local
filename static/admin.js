const adminForm = document.getElementById('admin-form');
const statsEl = document.getElementById('stats');
const errorEl = document.getElementById('admin-error');

adminForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorEl.textContent = '';

  const token = document.getElementById('token').value.trim();
  const res = await fetch(`/api/admin/stats?token=${encodeURIComponent(token)}`);
  const data = await res.json();

  if (!res.ok) {
    statsEl.classList.add('hidden');
    errorEl.textContent = data.error || 'Erreur admin';
    return;
  }

  statsEl.classList.remove('hidden');
  document.getElementById('total-guesses').textContent = data.total_guesses;
  document.getElementById('total-wins').textContent = data.total_wins;
  document.getElementById('avg-score').textContent = data.avg_score;

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
});
