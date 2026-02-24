"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface NewEventFormProps {
  title: string;
  agency: string;
  date: string;
  eventType: string;
  location: string;
  description: string;
  onTitleChange: (value: string) => void;
  onAgencyChange: (value: string) => void;
  onDateChange: (value: string) => void;
  onEventTypeChange: (value: string) => void;
  onLocationChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCreate: () => void;
}

export function NewEventForm({
  title,
  agency,
  date,
  eventType,
  location,
  description,
  onTitleChange,
  onAgencyChange,
  onDateChange,
  onEventTypeChange,
  onLocationChange,
  onDescriptionChange,
  onCreate,
}: NewEventFormProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>New Event</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
          placeholder="Event title"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-3">
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            type="datetime-local"
            value={date}
            onChange={(e) => onDateChange(e.target.value)}
          />
          <select
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            value={eventType}
            onChange={(e) => onEventTypeChange(e.target.value)}
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
            onChange={(e) => onAgencyChange(e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm bg-background"
            placeholder="Location"
            value={location}
            onChange={(e) => onLocationChange(e.target.value)}
          />
        </div>
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm bg-background"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
        />
        <Button size="sm" onClick={onCreate}>
          Create Event
        </Button>
      </CardContent>
    </Card>
  );
}
