"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { eventApi } from "@/lib/api";
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

export default function EventsPage() {
  const [events, setEvents] = useState<IndustryEvent[]>([]);
  const [upcoming, setUpcoming] = useState<IndustryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [view, setView] = useState<"upcoming" | "all">("upcoming");

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
      const [allEvents, upcomingEvents] = await Promise.all([
        eventApi.list(),
        eventApi.upcoming(),
      ]);
      setEvents(allEvents);
      setUpcoming(upcomingEvents);
    } catch {
      setError("Failed to load events.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
      fetchData();
    } catch {
      setError("Failed to create event.");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await eventApi.delete(id);
      fetchData();
    } catch {
      setError("Failed to delete event.");
    }
  };

  const displayed = view === "upcoming" ? upcoming : events;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Industry Days & Events"
        description="Track conferences, industry days, and pre-solicitation events"
        actions={
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Add Event"}
          </Button>
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
        </div>

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
                  <div key={ev.id} className="border rounded-lg p-4">
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
      </div>
    </div>
  );
}
