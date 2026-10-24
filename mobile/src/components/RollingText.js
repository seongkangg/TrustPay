// A number that rolls to its new value instead of jumping: 300ms, cubic ease-out, and interruptible
// (a new target starts from whatever is on screen). Each frame re-renders only this Text, so keep
// it to a few figures. Reduce Motion shows the new value at once.
import { useEffect, useRef, useState } from "react";
import { Text } from "react-native";

import useReduceMotion from "../useReduceMotion.js";

const DURATION = 300;

export function useRolling(target) {
  const reduce = useReduceMotion();
  const [display, setDisplay] = useState(target);
  const shown = useRef(target); // the value currently on screen, read when a new target arrives

  useEffect(() => {
    if (reduce || target == null) {
      shown.current = target;
      return undefined;
    }
    const from = shown.current ?? target;
    if (from === target) return undefined;
    const start = Date.now();
    let frame;
    const tick = () => {
      const p = Math.min(1, (Date.now() - start) / DURATION);
      const v = from + (target - from) * (1 - (1 - p) ** 3);
      shown.current = v;
      setDisplay(v);
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, reduce]);

  return reduce || target == null ? target : display;
}

// <RollingText value={1234.5} format={fmtMoney} style={...} /> — renders "—" for a missing value.
export default function RollingText({ value, format, style, ...rest }) {
  const shown = useRolling(value);
  return (
    <Text style={style} {...rest}>
      {shown == null ? "—" : format(shown)}
    </Text>
  );
}
