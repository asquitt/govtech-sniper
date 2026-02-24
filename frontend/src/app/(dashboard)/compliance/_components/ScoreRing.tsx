"use client";

interface ScoreRingProps {
  score: number;
}

export function ScoreRing({ score }: ScoreRingProps) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 70 ? "text-green-500" : score >= 40 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative w-36 h-36">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="currentColor"
          className="text-muted/30" strokeWidth="10" />
        <circle cx="64" cy="64" r={radius} fill="none" stroke="currentColor"
          className={color} strokeWidth="10" strokeDasharray={circumference}
          strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold">{score}%</span>
        <span className="text-xs text-muted-foreground">Compliance</span>
      </div>
    </div>
  );
}
