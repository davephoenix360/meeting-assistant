import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import CalendarAccount, CalendarAccountToken, CalendarEvent
from app.services.calendar.providers import (
    apply_refreshed_calendar_token,
    calendar_access_token_needs_refresh,
    fetch_provider_calendar_events,
    refresh_calendar_access_token,
    sync_calendar_account,
)
from app.services.calendar.token_crypto import TokenEncryptionError

logger = logging.getLogger(__name__)


def upsert_background_calendar_event(
    db: Session,
    account: CalendarAccount,
    payload: dict,
) -> tuple[CalendarEvent, bool]:
    event = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.calendar_account_id == account.id)
        .filter(CalendarEvent.external_event_id == payload["external_event_id"])
        .first()
    )
    created = event is None
    if event is None:
        event = CalendarEvent(
            workspace_id=account.workspace_id,
            calendar_account_id=account.id,
            external_event_id=payload["external_event_id"],
            title=payload["title"][:255],
        )
        db.add(event)

    event.title = payload["title"][:255]
    event.starts_at = payload.get("starts_at")
    event.ends_at = payload.get("ends_at")
    event.organizer_email = payload.get("organizer_email")
    event.meeting_url = payload.get("meeting_url")
    event.location = payload.get("location")
    event.description = payload.get("description")
    event.attendees_json = payload.get("attendees") or []
    event.artifacts_json = payload.get("artifacts") or []
    event.raw_json = payload.get("raw") or {}
    return event, created


async def sync_one_calendar_account(
    db: Session,
    account: CalendarAccount,
    token: CalendarAccountToken | None,
) -> dict:
    result = sync_calendar_account(account, token)
    if result["status"] != "ready":
        return result
    if token is None:
        return {
            "account_id": account.id,
            "provider": account.provider,
            "status": "not_connected",
            "message": "Connect this calendar with OAuth before background sync.",
        }

    refreshed = False
    try:
        if token and calendar_access_token_needs_refresh(token):
            refreshed_token = await refresh_calendar_access_token(account.provider, token)
            apply_refreshed_calendar_token(token, refreshed_token)
            refreshed = True
            db.commit()

        normalized_events = await fetch_provider_calendar_events(
            account,
            token,
            days_back=max(0, min(settings.calendar_background_sync_days_back, 365)),
            days_forward=max(0, min(settings.calendar_background_sync_days_forward, 365)),
            limit=max(1, min(settings.calendar_background_sync_max_results, 1000)),
            max_pages=max(1, min(settings.calendar_background_sync_max_pages, 20)),
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401 and token:
            refreshed_token = await refresh_calendar_access_token(account.provider, token)
            apply_refreshed_calendar_token(token, refreshed_token)
            refreshed = True
            db.commit()
            normalized_events = await fetch_provider_calendar_events(
                account,
                token,
                days_back=max(0, min(settings.calendar_background_sync_days_back, 365)),
                days_forward=max(0, min(settings.calendar_background_sync_days_forward, 365)),
                limit=max(1, min(settings.calendar_background_sync_max_results, 1000)),
                max_pages=max(1, min(settings.calendar_background_sync_max_pages, 20)),
            )
        else:
            raise

    imported = 0
    updated = 0
    for event_payload in normalized_events:
        _, created = upsert_background_calendar_event(db, account, event_payload)
        if created:
            imported += 1
        else:
            updated += 1

    account.last_sync_at = func.now()
    account.provider_metadata_json = {
        **(account.provider_metadata_json or {}),
        "last_background_sync_result": {
            "source": "background",
            "status": "synced",
            "imported": imported,
            "updated": updated,
            "token_refreshed": refreshed,
            "events_scanned": len(normalized_events),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
        "last_background_sync_error": {},
    }
    db.commit()
    return {
        "account_id": account.id,
        "provider": account.provider,
        "status": "synced",
        "events_imported": imported,
        "events_updated": updated,
        "token_refreshed": refreshed,
        "events_scanned": len(normalized_events),
    }


async def run_calendar_sync_once() -> list[dict]:
    db = SessionLocal()
    try:
        accounts = (
            db.query(CalendarAccount, CalendarAccountToken)
            .join(
                CalendarAccountToken,
                CalendarAccountToken.calendar_account_id == CalendarAccount.id,
            )
            .filter(CalendarAccount.status == "connected")
            .filter(CalendarAccount.provider != "local")
            .all()
        )

        results: list[dict] = []
        for account, token in accounts:
            try:
                results.append(await sync_one_calendar_account(db, account, token))
            except (TokenEncryptionError, httpx.HTTPError, ValueError) as e:
                account_id = account.id
                provider = account.provider
                db.rollback()
                record_background_sync_failure(db, account_id, provider, e)
                logger.warning(
                    "Background calendar sync failed for account %s: %s",
                    account_id,
                    e,
                )
                results.append(
                    {
                        "account_id": account_id,
                        "provider": provider,
                        "status": "failed",
                        "message": str(e),
                    }
                )
        return results
    finally:
        db.close()


def record_background_sync_failure(
    db: Session,
    account_id: int,
    provider: str,
    error: Exception,
) -> None:
    account = db.get(CalendarAccount, account_id)
    if not account:
        return
    account.provider_metadata_json = {
        **(account.provider_metadata_json or {}),
        "last_background_sync_error": {
            "source": "background",
            "status": "failed",
            "provider": provider,
            "message": str(error),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    db.commit()


async def calendar_sync_loop(stop_event: asyncio.Event) -> None:
    interval = max(60, settings.calendar_background_sync_interval_seconds)
    while not stop_event.is_set():
        try:
            await run_calendar_sync_once()
        except Exception as e:
            logger.exception("Background calendar sync loop failed: %s", e)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
