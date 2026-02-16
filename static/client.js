const form = document.getElementById('guess-form');
const historyEl = document.getElementById('history');
const progressBarEl = document.getElementById('progress-bar');
const progressTextEl = document.getElementById('progress-text');
const victoryScreenEl = document.getElementById('victory-screen');
const guessInputEl = document.getElementById('guess');
const pseudoInputEl = document.getElementById('pseudo');

const todayKey = new Date().toISOString().slice(0, 10);
const storageKey = `cemantix-won-${todayKey}`;
let maxScore = 0;
let isLocked = localStorage.getItem(storageKey) === '1';

function setLockState(locked) {
  isLocked = locked;
  form.querySelector('button').disabled = locked;
  guessInputEl.disabled = locked;
  pseudoInputEl.disabled = locked;
  victoryScreenEl.classList.toggle('hidden', !locked);
}

function updateProgress(score) {
  maxScore = Math.max(maxScore, score);
  progressBarEl.style.width = `${maxScore}%`;
  progressBarEl.textContent = `${maxScore}%`;
  progressTextEl.textContent = `Meilleur score : ${maxScore}/100`;
}

setLockState(isLocked);

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  if (isLocked) {
    return;
  }

  const guess = guessInputEl.value.trim();
  const pseudo = pseudoInputEl.value.trim();

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

  updateProgress(data.score);

  const li = document.createElement('li');
  li.textContent = `${data.guess} → score ${data.score}/100 - ${data.message}`;
  if (data.is_win) {
    li.classList.add('win');
    localStorage.setItem(storageKey, '1');
    setLockState(true);
  }
  historyEl.prepend(li);

  guessInputEl.value = '';
});
