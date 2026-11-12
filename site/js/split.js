// Draggable divider. Sets a CSS variable (a percentage of the container) that sizes the first panel.
export function makeSplitter(handle, { container, cssVar, axis, min, max, initial, storageKey, onResize }) {
  const clamp = (v) => Math.min(max, Math.max(min, v));
  let value = clamp(Number(localStorage.getItem(storageKey)) || initial);

  function apply(save) {
    container.style.setProperty(cssVar, `${value}%`);
    handle.setAttribute('aria-valuenow', Math.round(value));
    if (save) localStorage.setItem(storageKey, value);
    onResize?.();
  }

  handle.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    handle.setPointerCapture(e.pointerId);
    handle.classList.add('dragging');
    document.body.classList.add('resizing');
    const box = container.getBoundingClientRect();
    handle.onpointermove = (ev) => {
      value = clamp(axis === 'y'
        ? ((ev.clientY - box.top) / box.height) * 100
        : ((ev.clientX - box.left) / box.width) * 100);
      apply(false);
    };
    handle.onpointerup = handle.onpointercancel = () => {
      handle.onpointermove = handle.onpointerup = handle.onpointercancel = null;
      handle.classList.remove('dragging');
      document.body.classList.remove('resizing');
      apply(true);
    };
  });

  handle.addEventListener('dblclick', () => { value = initial; apply(true); });

  // Keyboard: arrows move the divider in 5% steps.
  handle.addEventListener('keydown', (e) => {
    const step = { ArrowUp: -5, ArrowLeft: -5, ArrowDown: 5, ArrowRight: 5 }[e.key];
    if (!step) return;
    e.preventDefault();
    value = clamp(value + step);
    apply(true);
  });

  apply(false);
}
