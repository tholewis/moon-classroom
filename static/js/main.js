// ─── Star Field ───────────────────────────────────────────────
(function generateStars() {
  const container = document.getElementById('stars');
  if (!container) return;

  const count = 200;
  const fragment = document.createDocumentFragment();

  for (let i = 0; i < count; i++) {
    const star = document.createElement('div');
    star.className = 'star';
    const size = Math.random() * 2.5 + 0.5;
    const x = Math.random() * 100;
    const y = Math.random() * 100;
    const duration = (Math.random() * 4 + 2).toFixed(2);
    const minOpacity = (Math.random() * 0.2 + 0.1).toFixed(2);
    const maxOpacity = (Math.random() * 0.5 + 0.4).toFixed(2);
    const delay = (Math.random() * 5).toFixed(2);

    star.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${x}%;
      top: ${y}%;
      --duration: ${duration}s;
      --min-opacity: ${minOpacity};
      --max-opacity: ${maxOpacity};
      animation-delay: ${delay}s;
    `;
    fragment.appendChild(star);
  }

  container.appendChild(fragment);
})();


// ─── Moon Visual ──────────────────────────────────────────────
function initMoonVisual(phase) {
  const overlay = document.getElementById('shadow-overlay');
  if (!overlay) return;

  // phase: 0 = new moon, 0.5 = full moon, 1 = new moon again
  // The shadow is a dark circle overlaid on the bright moon surface.
  // Moving it creates realistic crescent shapes via overflow:hidden clipping.
  //
  // Waxing (0→0.5): dark circle slides from left=0% to left=100% (lit grows on left)
  // Waning (0.5→1): dark circle slides from left=0% (offscreen left) back to left=0%

  if (phase <= 0.5) {
    // Waxing: shadow circle moves right, revealing lit surface on the left
    overlay.style.left = `${phase * 200}%`;
    overlay.style.right = 'auto';
    overlay.style.width = '100%';
    overlay.style.borderRadius = '50%';
  } else {
    // Waning: shadow circle grows from the right, covering lit surface on the left
    const coverPct = (phase - 0.5) * 200; // 0% → 100%
    overlay.style.right = '0';
    overlay.style.left = 'auto';
    overlay.style.width = `${coverPct}%`;
    overlay.style.borderRadius = '50% 0 0 50%';
  }
}


// ─── Date Explorer ────────────────────────────────────────────
document.getElementById('explore-btn').addEventListener('click', async () => {
  const dateInput = document.getElementById('date-input');
  const dateVal = dateInput.value;
  if (!dateVal) return;

  const btn = document.getElementById('explore-btn');
  btn.textContent = '…';
  btn.disabled = true;

  try {
    const res = await fetch(`/api/moon?date=${dateVal}`);
    if (!res.ok) throw new Error('API error');
    const data = await res.json();

    document.getElementById('result-moon-emoji').textContent = data.emoji;
    document.getElementById('result-phase-name').textContent = data.phase_name;
    document.getElementById('result-illumination').textContent = `${data.illumination}%`;
    document.getElementById('result-age').textContent = `${data.age} days`;
    document.getElementById('result-days-to-full').textContent =
      data.days_to_full < 0.5 ? 'Tonight!' : `${data.days_to_full} days`;

    const desc = document.getElementById('result-description');
    if (data.lesson && data.lesson.description) {
      desc.textContent = data.lesson.description;
      desc.style.display = 'block';
    } else {
      desc.style.display = 'none';
    }

    const result = document.getElementById('explorer-result');
    result.classList.remove('hidden');
    result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (e) {
    console.error(e);
  } finally {
    btn.textContent = 'Explore';
    btn.disabled = false;
  }
});

// Allow pressing Enter in date input
document.getElementById('date-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('explore-btn').click();
});
