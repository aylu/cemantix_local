const form = document.getElementById('guess-form');
const historyEl = document.getElementById('history');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const guess = document.getElementById('guess').value.trim();
  const pseudo = document.getElementById('pseudo').value.trim();

  if (!guess) {
    return;
  }

  const res = await fetch('/api/guess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ guess, pseudo }),
  });

  const data = await res.json();
  if (!res.ok) {
    alert(data.error || 'Erreur inconnue');
    return;
  }

  const li = document.createElement('li');
  li.textContent = `${data.guess} → score ${data.score}/100 - ${data.message}`;
  if (data.is_win) {
    li.classList.add('win');
  }
  historyEl.prepend(li);

  document.getElementById('guess').value = '';
});
