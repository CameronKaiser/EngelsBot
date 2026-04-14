import os
import json
import asyncio
import Configuration

from functools import partial
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GoogleApi:
    def __init__(self):
        credential_json = json.loads(Configuration.GOOGLE_CREDENTIAL_JSON)
        self.credentials = Credentials.from_authorized_user_info(credential_json)
        self.api = build("calendar", "v3", credentials=self.credentials)
        self.RATE_LIMIT    = 10
        self.WINDOW_LENGTH = 1

    async def arbitrate_rate(self):



    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(func, *args, **kwargs)
        )

    async def add_event(self, calendar_id: str, event_body: dict):
        """Public async method your bot will call."""
        async with self.rate_limiter:
            # Build the request (sync)
            request = self.api.events().insert(
                calendarId=calendar_id,
                body=event_body
            )

            # Execute the request (sync → async)
            return await self._run(request.execute)

    async def delete_event(self, calendar_id: str, event_id: str):
        async with self.rate_limiter:
            request = self.api.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            )
            return await self._run(request.execute)

    async def update_event(self, calendar_id: str, event_id: str, event_body: dict):
        async with self.rate_limiter:
            request = self.api.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event_body
            )
            return await self._run(request.execute)
