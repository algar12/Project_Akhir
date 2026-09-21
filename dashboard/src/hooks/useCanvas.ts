import { useRef, useEffect } from 'react';

type DrawFunction = (ctx: CanvasRenderingContext2D, width: number, height: number) => void;

export function useCanvas(draw: DrawFunction) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawRef = useRef<DrawFunction>(draw);
  drawRef.current = draw;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (!parent) return;

    let animId: number;

    const render = () => {
      const rect = parent.getBoundingClientRect();
      const targetW = Math.floor(rect.width);
      const targetH = Math.floor(rect.height);
      if (targetW === 0 || targetH === 0) return;

      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
      }
      const ctx = canvas.getContext('2d');
      if (ctx && drawRef.current) {
        drawRef.current(ctx, targetW, targetH);
      }
    };

    const resizeObserver = new ResizeObserver(() => {
      cancelAnimationFrame(animId);
      animId = requestAnimationFrame(render);
    });

    resizeObserver.observe(parent);
    render();

    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
    };
  }, []);

  // Re-render when draw function or its reactive dependencies change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || canvas.width === 0 || canvas.height === 0) return;
    const ctx = canvas.getContext('2d');
    if (ctx && drawRef.current) {
      drawRef.current(ctx, canvas.width, canvas.height);
    }
  }, [draw]);

  return canvasRef;
}
