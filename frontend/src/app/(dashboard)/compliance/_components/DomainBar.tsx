"use client";

interface DomainBarProps {
  name: string;
  percentage: number;
}

export function DomainBar({ name, percentage }: DomainBarProps) {
  const color = percentage >= 70 ? "bg-green-500" : percentage >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="truncate mr-2">{name}</span>
        <span className="font-medium flex-shrink-0">{percentage}%</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}
