"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { IndustryEvent } from "@/types";

interface EventCalendarProps {
  calendarLabel: string;
  calendarMonth: number;
  calendarLoading: boolean;
  calendarDays: Date[];
  calendarEventsByDay: Record<string, IndustryEvent[]>;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

function localDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function EventCalendar({
  calendarLabel,
  calendarMonth,
  calendarLoading,
  calendarDays,
  calendarEventsByDay,
  onPrevMonth,
  onNextMonth,
}: EventCalendarProps) {
  return (
    <Card data-testid="events-calendar-card">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle>Event Calendar • {calendarLabel}</CardTitle>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={onPrevMonth}>
              Prev
            </Button>
            <Button size="sm" variant="outline" onClick={onNextMonth}>
              Next
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {calendarLoading ? (
          <div className="animate-pulse space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-2" data-testid="events-calendar-grid">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((dayLabel) => (
              <div
                key={dayLabel}
                className="text-xs font-medium text-muted-foreground px-2 py-1"
              >
                {dayLabel}
              </div>
            ))}
            {calendarDays.map((day) => {
              const inCurrentMonth = day.getMonth() === calendarMonth - 1;
              const key = localDateKey(day);
              const dayEvents = calendarEventsByDay[key] || [];
              return (
                <div
                  key={key}
                  className={`min-h-[96px] rounded-md border p-2 ${
                    inCurrentMonth ? "bg-background" : "bg-muted/30 text-muted-foreground"
                  }`}
                >
                  <p className="text-xs font-medium">{day.getDate()}</p>
                  <div className="mt-1 space-y-1">
                    {dayEvents.slice(0, 2).map((ev) => (
                      <p
                        key={ev.id}
                        className="truncate rounded bg-primary/10 px-1.5 py-0.5 text-[10px]"
                        title={ev.title}
                      >
                        {ev.title}
                      </p>
                    ))}
                    {dayEvents.length > 2 && (
                      <p className="text-[10px] text-muted-foreground">
                        +{dayEvents.length - 2} more
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
