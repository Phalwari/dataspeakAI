import React, { useEffect, useState } from "react";

interface AnimatedNumberProps {
  value: string | number;
  duration?: number;
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({ value, duration = 1000 }) => {
  const [displayStr, setDisplayStr] = useState<string>("0");

  useEffect(() => {
    if (value === undefined || value === null) {
      setDisplayStr("0");
      return;
    }

    const strValue = String(value);
    // Match numeric portion
    const match = strValue.match(/^([^0-9.-]*)([0-9.,]+)(.*)$/);

    if (!match) {
      setDisplayStr(strValue);
      return;
    }

    const prefix = match[1] || "";
    const numStr = match[2].replace(/,/g, "");
    const suffix = match[3] || "";
    const targetNum = parseFloat(numStr);

    if (isNaN(targetNum)) {
      setDisplayStr(strValue);
      return;
    }

    const steps = 30;
    const stepTime = Math.max(duration / steps, 16);
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      const progress = currentStep / steps;
      const easeProgress = 1 - Math.pow(1 - progress, 3); // cubic ease-out
      const currentNum = targetNum * easeProgress;

      const formattedNum = Number.isInteger(targetNum)
        ? Math.round(currentNum).toLocaleString()
        : currentNum.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

      setDisplayStr(`${prefix}${formattedNum}${suffix}`);

      if (currentStep >= steps) {
        clearInterval(timer);
        setDisplayStr(strValue);
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [value, duration]);

  return <span>{displayStr}</span>;
};
