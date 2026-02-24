"use client";

import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { eventApi } from "@/lib/api";
import type { EventAlert, IndustryEvent } from "@/types";
import { EventAlerts } from "./_components/EventAlerts";
import { NewEventForm } from "./_components/NewEventForm";
import { EventCalendar } from "./_components/EventCalendar";
import { EventList } from "./_components/EventList";

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

  const handlePrevMonth = () => {
    if (calendarMonth === 1) {
      setCalendarMonth(12);
      setCalendarYear((prev) => prev - 1);
    } else {
      setCalendarMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (calendarMonth === 12) {
      setCalendarMonth(1);
      setCalendarYear((prev) => prev + 1);
    } else {
      setCalendarMonth((prev) => prev + 1);
    }
  };

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

        <EventAlerts alerts={alerts} />

        {showForm && (
          <NewEventForm
            title={title}
            agency={agency}
            date={date}
            eventType={eventType}
            location={location}
            description={description}
            onTitleChange={setTitle}
            onAgencyChange={setAgency}
            onDateChange={setDate}
            onEventTypeChange={setEventType}
            onLocationChange={setLocation}
            onDescriptionChange={setDescription}
            onCreate={handleCreate}
          />
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
          <EventCalendar
            calendarLabel={calendarLabel}
            calendarMonth={calendarMonth}
            calendarLoading={calendarLoading}
            calendarDays={calendarDays}
            calendarEventsByDay={calendarEventsByDay}
            onPrevMonth={handlePrevMonth}
            onNextMonth={handleNextMonth}
          />
        ) : (
          <EventList
            view={view}
            events={displayed}
            loading={loading}
            onDelete={handleDelete}
          />
        )}
      </div>
    </div>
  );
}
