import { useEffect, useRef } from "react";

const STAR_COUNT_PER_MEGAPIXEL = 95;

function createStars(width, height) {
  const count = Math.min(
    280,
    Math.max(90, Math.round((width * height) / 1_000_000 * STAR_COUNT_PER_MEGAPIXEL)),
  );
  return Array.from({ length: count }, () => ({
    x: Math.random(),
    y: Math.random(),
    radius: Math.random() * 1.1 + 0.25,
    alpha: Math.random() * 0.45 + 0.2,
    depth: Math.random() * 0.8 + 0.2,
    phase: Math.random() * Math.PI * 2,
  }));
}

export default function SpaceBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const context = canvas.getContext("2d");
    if (!context) return undefined;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let width = 0;
    let height = 0;
    let pixelRatio = 1;
    let stars = [];
    let frameId;
    let startedAt = performance.now();

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = Math.round(width * pixelRatio);
      canvas.height = Math.round(height * pixelRatio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      stars = createStars(width, height);
    }

    function draw(timestamp) {
      const elapsed = (timestamp - startedAt) / 1000;
      context.clearRect(0, 0, width, height);

      for (const star of stars) {
        const drift = reducedMotion.matches ? 0 : elapsed * star.depth * 2.2;
        const x = (star.x * width + drift) % (width + 12) - 6;
        const y = star.y * height;
        const twinkle = reducedMotion.matches
          ? 1
          : 0.82 + Math.sin(elapsed * 1.4 + star.phase) * 0.18;

        context.beginPath();
        context.fillStyle = `rgba(181, 226, 235, ${star.alpha * twinkle})`;
        context.arc(x, y, star.radius, 0, Math.PI * 2);
        context.fill();
      }

      if (!reducedMotion.matches) {
        const cometCycle = elapsed % 18;
        if (cometCycle > 12 && cometCycle < 13.8) {
          const progress = (cometCycle - 12) / 1.8;
          const x = width * (0.08 + progress * 0.72);
          const y = height * (0.12 + progress * 0.26);
          const gradient = context.createLinearGradient(x - 90, y - 32, x, y);
          gradient.addColorStop(0, "rgba(114, 228, 192, 0)");
          gradient.addColorStop(1, "rgba(173, 239, 232, 0.72)");
          context.strokeStyle = gradient;
          context.lineWidth = 1.3;
          context.beginPath();
          context.moveTo(x - 90, y - 32);
          context.lineTo(x, y);
          context.stroke();
        }
      }

      if (!reducedMotion.matches) frameId = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize);
    draw(performance.now());
    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return <canvas ref={canvasRef} className="space-background" aria-hidden="true" />;
}
