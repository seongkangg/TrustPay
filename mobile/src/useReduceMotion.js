// Follows the system Reduce Motion setting, live.
import { useEffect, useState } from "react";
import { AccessibilityInfo } from "react-native";

export default function useReduceMotion() {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduce);
    const sub = AccessibilityInfo.addEventListener("reduceMotionChanged", setReduce);
    return () => sub.remove();
  }, []);
  return reduce;
}
