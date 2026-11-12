// Draws a three.js scene only while its canvas is on screen: every frame while something is moving,
// ~30 fps while it is only idling (a slow spin looks the same at about half the CPU/GPU cost).
// draw(time, f) gets f = how many 60 fps frames of time passed, so motion speed doesn't depend on the frame rate.
const IDLE_MS = 1000 / 30;

export function frameLoop(renderer, host, draw, moving = () => true) {
  let last = null;
  const tick = (t) => {
    if (last !== null && !moving() && t - last < IDLE_MS - 4) return;
    const f = last === null ? 1 : Math.min(t - last, 100) / (1000 / 60);
    last = t;
    draw(t, f);
  };
  new IntersectionObserver(([e]) => {
    last = null;
    renderer.setAnimationLoop(e.isIntersecting ? tick : null);
  }).observe(host);
}

// Per-frame easing factor `k` (written for 60 fps) adjusted for f frames.
export const damp = (k, f) => 1 - (1 - k) ** f;
