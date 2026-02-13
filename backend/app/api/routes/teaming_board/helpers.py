"""Teaming Board helper functions."""

from fastapi import HTTPException

from app.models.capture import (
    TeamingDigestChannel,
    TeamingDigestFrequency,
    TeamingDigestSchedule,
)
from app.schemas.teaming import TeamingDigestScheduleRead


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _parse_teaming_frequency(value: str) -> TeamingDigestFrequency:
    try:
        return TeamingDigestFrequency(value)
    except ValueError as exc:
        raise HTTPException(400, "Invalid digest frequency") from exc


def _parse_teaming_channel(value: str) -> TeamingDigestChannel:
    try:
        return TeamingDigestChannel(value)
    except ValueError as exc:
        raise HTTPException(400, "Invalid digest channel") from exc


def _serialize_teaming_digest_schedule(
    schedule: TeamingDigestSchedule,
) -> TeamingDigestScheduleRead:
    return TeamingDigestScheduleRead(
        frequency=_enum_value(schedule.frequency),
        day_of_week=schedule.day_of_week,
        hour_utc=schedule.hour_utc,
        minute_utc=schedule.minute_utc,
        channel=_enum_value(schedule.channel),
        include_declined_reasons=schedule.include_declined_reasons,
        is_enabled=schedule.is_enabled,
        last_sent_at=schedule.last_sent_at,
    )
