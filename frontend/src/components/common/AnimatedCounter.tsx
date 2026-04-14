import { useEffect, useRef, useState } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

interface AnimatedCounterProps {
  target: number;
  duration?: number;
  suffix?: string;
  decimals?: number;
  className?: string;
}

export function AnimatedCounter({
  target,
  duration = 1500,
  suffix = '',
  decimals = 1,
  className = '',
}: AnimatedCounterProps) {
  const [current, setCurrent] = useState(0);
  const reducedMotion = usePrefersReducedMotion();
  const frameRef = useRef<number>(0);
  const displayValue = reducedMotion ? target : current;

  useEffect(() => {
    if (reducedMotion) {
      return;
    }

    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      setCurrent(target * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration, reducedMotion]);

  return (
    <span className={className} aria-label={`${target.toFixed(decimals)}${suffix}`}>
      {displayValue.toFixed(decimals)}
      {suffix}
    </span>
  );
}
