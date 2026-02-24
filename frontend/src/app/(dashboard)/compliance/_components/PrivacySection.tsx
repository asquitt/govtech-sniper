"use client";

interface PrivacySectionProps {
  title: string;
  items: string[];
}

export function PrivacySection({ title, items }: PrivacySectionProps) {
  return (
    <div>
      <p className="text-sm font-medium mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="text-xs text-muted-foreground flex items-start gap-2">
            <span className="mt-1.5 w-1 h-1 rounded-full bg-primary flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
