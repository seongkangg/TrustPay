// A figure that rolls to its new value instead of jumping: 300ms, cubic ease-out, interruptible (a
// new target starts from whatever is on screen). The first real value appears as is. Reduced motion
// shows new values at once. Each frame re-renders only this span.
import { useEffect, useRef, useState } from "react";

const DURATION = 300;
const REDUCED_MOTION =
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function useRolling(target) {
  const [display, setDisplay] = useState(target);
  const shown = useRef(target); // the value currently on screen, read when a new target arrives

  useEffect(() => {
    if (REDUCED_MOTION || target == null) {
      shown.current = target;
      return undefined;
    }
    const from = shown.current;
    if (from == null) {
      shown.current = target;
      const frame = window.requestAnimationFrame(() => setDisplay(target));
      return () => window.cancelAnimationFrame(frame);
    }
    if (from === target) return undefined;
    const start = window.performance.now();
    let frame;
    const tick = (now) => {
      const p = Math.min(1, (now - start) / DURATION);
      const v = from + (target - from) * (1 - (1 - p) ** 3);
      shown.current = v;
      setDisplay(v);
      if (p < 1) frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [target]);

  return REDUCED_MOTION || target == null ? target : (display ?? target);
}

// <RollingNumber value={1234.5} format={fmtMoney} className="figure" /> — "—" for a missing value.
export default function RollingNumber({ value, format, ...rest }) {
  const shown = useRolling(value);
  return <span {...rest}>{shown == null ? "—" : format(shown)}</span>;
}
