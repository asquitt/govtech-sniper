"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IndustryEvent } from "@/types";

const EVENT_TYPE_LABELS: Record<string, string> = {
  industry_day: "Industry Day",
  pre_solicitation: "Pre-Solicitation",
  conference: "Conference",
  webinar: "Webinar",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface EventListProps {
  view: "upcoming" | "all";
  events: IndustryEvent[];
  loading: boolean;
  onDelete: (id: number) => void;
}

export function EventList({ view, events, loading, onDelete }: EventListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {view === "upcoming" ? "Upcoming Events" : "All Events"}{" "}
          <Badge variant="secondary">{events.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <p className="text-muted-foreground text-sm text-center py-8">
            No events found. Add events to track industry days and conferences.
          </p>
        ) : (
          <div className="space-y-3">
            {events.map((ev) => (
              <div key={ev.id} className="border rounded-lg p-4" data-testid="event-list-row">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{ev.title}</p>
                    <div className="flex gap-2 mt-1 text-xs text-muted-foreground">
                      <span>{formatDate(ev.date)}</span>
                      {ev.agency && <span>{ev.agency}</span>}
                      {ev.location && <span>{ev.location}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">
                      {EVENT_TYPE_LABELS[ev.event_type] || ev.event_type}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(ev.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
                {ev.description && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {ev.description}
                  </p>
                )}
                {ev.registration_url && (
                  <a
                    href={ev.registration_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline mt-1 inline-block"
                  >
                    Register
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
