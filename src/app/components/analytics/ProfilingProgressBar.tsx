import React, { useEffect, useState } from "react";

interface ProfilingProgressBarProps {
  isProfiling: boolean;
  onComplete?: () => void;
}

const PROFILING_STEPS = [
  { label: "Introspecting database schema & active tables...", progress: 25 },
  { label: "Computing column totals, averages & row counts...", progress: 55 },
  { label: "Generating AI business summary & anomaly reports...", progress: 85 },
  { label: "Finalizing Live KPI Dashboard!", progress: 100 }
];

export const ProfilingProgressBar: React.FC<ProfilingProgressBarProps> = ({ isProfiling, onComplete }) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    if (!isProfiling) {
      setCurrentStepIndex(0);
      return;
    }

    const t1 = setTimeout(() => setCurrentStepIndex(1), 1200);
    const t2 = setTimeout(() => setCurrentStepIndex(2), 2400);
    const t3 = setTimeout(() => {
      setCurrentStepIndex(3);
      if (onComplete) onComplete();
    }, 3600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [isProfiling, onComplete]);

  if (!isProfiling) return null;

  const activeStep = PROFILING_STEPS[currentStepIndex];

  return (
    <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-4 shadow-lg space-y-3 animate-in fade-in duration-300">
      <div className="flex items-center justify-between text-xs font-medium">
        <span className="flex items-center gap-2 text-blue-400">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
          {activeStep.label}
        </span>
        <span className="font-mono text-slate-400">{activeStep.progress}%</span>
      </div>
      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
        <div 
          className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-500 ease-out"
          style={{ width: `${activeStep.progress}%` }}
        />
      </div>
    </div>
  );
};
