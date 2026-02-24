"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SocketEvent {
  type: string;
  timestamp: string;
  detail?: string;
}

interface RecentEventsProps {
  events: SocketEvent[];
  eventFilter: string;
  filterOptions: readonly string[];
  onFilterChange: (value: string) => void;
}

export function RecentEvents({
  events,
  eventFilter,
  filterOptions,
  onFilterChange,
}: RecentEventsProps) {
  return (
    <Card className="border border-border">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Recent Events</CardTitle>
          <select
            aria-label="Event filter"
            className="rounded-md border border-border bg-background px-2 py-1 text-xs"
            value={eventFilter}
            onChange={(event) => onFilterChange(event.target.value)}
          >
            {filterOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No events captured yet.</p>
        ) : (
          <div className="space-y-2">
            {events.map((item, index) => (
              <div
                key={`${item.timestamp}-${item.type}-${index}`}
                className="rounded-md border border-border px-3 py-2 text-xs"
              >
                <p className="font-medium">{item.type}</p>
                <p className="text-muted-foreground">{new Date(item.timestamp).toLocaleString()}</p>
                {item.detail ? <p className="text-muted-foreground">{item.detail}</p> : null}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
