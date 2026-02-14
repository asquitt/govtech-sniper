"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { eventApi } from "@/lib/api";
import type { EventAlert, IndustryEvent } from "@/types";

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

function localDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildCalendarGrid(month: number, year: number): Date[] {
  const firstOfMonth = new Date(year, month - 1, 1);
  const gridStart = new Date(firstOfMonth);
  gridStart.setDate(firstOfMonth.getDate() - firstOfMonth.getDay());
  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(gridStart);
    day.setDate(gridStart.getDate() + index);
    return day;
  });
}

export default function EventsPage() {
  const [events, setEvents] = useState<IndustryEvent[]>([]);
  const [upcoming, setUpcoming] = useState<IndustryEvent[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<IndustryEvent[]>([]);
  const [alerts, setAlerts] = useState<EventAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [ingestSummary, setIngestSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState<"upcoming" | "all" | "calendar">("upcoming");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date().getMonth() + 1);
  const [calendarYear, setCalendarYear] = useState(() => new Date().getFullYear());

  // Form state
  const [title, setTitle] = useState("");
  const [agency, setAgency] = useState("");
  const [date, setDate] = useState("");
  const [eventType, setEventType] = useState("industry_day");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [allEvents, upcomingEvents, alertResponse] = await Promise.all([
        eventApi.list(),
        eventApi.upcoming(),
        eventApi.alerts(),
      ]);
      setEvents(allEvents);
      setUpcoming(upcomingEvents);
      setAlerts(alertResponse.alerts);
    } catch {
      setError("Failed to load events.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCalendar = useCallback(async () => {
    setCalendarLoading(true);
    try {
      const data = await eventApi.calendar(calendarMonth, calendarYear);
      setCalendarEvents(data);
    } catch {
      setError("Failed to load calendar view.");
    } finally {
      setCalendarLoading(false);
    }
  }, [calendarMonth, calendarYear]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    loadCalendar();
  }, [loadCalendar]);

  const handleCreate = async () => {
    if (!title.trim() || !date) return;
    try {
      await eventApi.create({
        title: title.trim(),
        date,
        agency: agency || undefined,
        event_type: eventType,
        location: location || undefined,
        description: description || undefined,
      });
      setTitle("");
      setAgency("");
      setDate("");
      setEventType("industry_day");
      setLocation("");
      setDescription("");
      setShowForm(false);
      setIngestSummary(null);
      await Promise.all([fetchData(), loadCalendar()]);
    } catch {
      setError("Failed to create event.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await eventApi.delete(id);
      setIngestSummary(null);
      await Promise.all([fetchData(), loadCalendar()]);
    } catch {
      setError("Failed to delete event.");
    }
  };

  const handleIngest = async () => {
    setIngesting(true);
    setError(null);
    try {
      const result = await eventApi.ingest({ days_ahead: 120, include_curated: true });
      setIngestSummary(
        `Ingestion completed: ${result.created} new events, ${result.existing} already tracked.`
      );
      await Promise.all([fetchData(), loadCalendar()]);
    } catch {
      setError("Failed to ingest events from sources.");
    } finally {
      setIngesting(false);
    }
  };

  const displayed = view === "upcoming" ? upcoming : events;
  const calendarDays = buildCalendarGrid(calendarMonth, calendarYear);
  const calendarEventsByDay = calendarEvents.reduce<Record<string, IndustryEvent[]>>((acc, item) => {
    const key = localDateKey(new Date(item.date));
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {});
  const calendarLabel = new Date(calendarYear, calendarMonth - 1, 1).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Industry Days & Events"
        description="Track conferences, industry days, and pre-solicitation events"
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleIngest} disabled={ingesting}>
              {ingesting ? "Ingesting..." : "Ingest from Sources"}
            </Button>
            <Button size="sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "Add Event"}
            </Button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {error && (
          <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {ingestSummary && (
          <div
            data-testid="events-ingest-summary"
            className="rounded-lg border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800"
          >
            {ingestSummary}
          </div>
        )}

        <Card data-testid="events-alerts-card">
          <CardHeader>
            <CardTitle>
              Relevant Event Alerts <Badge variant="secondary">{alerts.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No high-confidence event alerts yet. Add agency and keyword preferences in Signals
                subscription settings to improve matching.
              </p>
            ) : (
              <div className="space-y-3">
                {alerts.slice(0, 6).map((alert) => (
                  <div
                    key={alert.event.id}
                    className="rounded-lg border p-3"
                    data-testid="event-alert-row"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{alert.event.title}</p>
                      <Badge variant="outline">{Math.round(alert.relevance_score)}%</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      In {alert.days_until_event} day(s) • {alert.match_reasons.join(" • ")}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>New Event</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Event title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-3">
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  type="datetime-local"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
                <select
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value)}
                >
                  <option value="industry_day">Industry Day</option>
                  <option value="pre_solicitation">Pre-Solicitation</option>
                  <option value="conference">Conference</option>
                  <option value="webinar">Webinar</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  placeholder="Agency"
                  value={agency}
                  onChange={(e) => setAgency(e.target.value)}
                />
                <input
                  className="border rounded-lg px-3 py-2 text-sm bg-background"
                  placeholder="Location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                />
              </div>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
                placeholder="Description (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <Button size="sm" onClick={handleCreate}>
                Create Event
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="flex gap-2">
          <Button
            variant={view === "upcoming" ? "default" : "outline"}
            size="sm"
            onClick={() => setView("upcoming")}
          >
            Upcoming (30 days)
          </Button>
          <Button
            variant={view === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setView("all")}
          >
            All Events
          </Button>
          <Button
            variant={view === "calendar" ? "default" : "outline"}
            size="sm"
            onClick={() => setView("calendar")}
          >
            Calendar
          </Button>
        </div>

        {view === "calendar" ? (
          <Card data-testid="events-calendar-card">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle>Event Calendar • {calendarLabel}</CardTitle>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (calendarMonth === 1) {
                        setCalendarMonth(12);
                        setCalendarYear((prev) => prev - 1);
                      } else {
                        setCalendarMonth((prev) => prev - 1);
                      }
                    }}
                  >
                    Prev
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (calendarMonth === 12) {
                        setCalendarMonth(1);
                        setCalendarYear((prev) => prev + 1);
                      } else {
                        setCalendarMonth((prev) => prev + 1);
                      }
                    }}
                  >
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
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>
                {view === "upcoming" ? "Upcoming Events" : "All Events"}{" "}
                <Badge variant="secondary">{displayed.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="animate-pulse space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-muted rounded" />
                  ))}
                </div>
              ) : displayed.length === 0 ? (
                <p className="text-muted-foreground text-sm text-center py-8">
                  No events found. Add events to track industry days and conferences.
                </p>
              ) : (
                <div className="space-y-3">
                  {displayed.map((ev) => (
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
                            onClick={() => handleDelete(ev.id)}
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
        )}
      </div>
    </div>
  );
}
