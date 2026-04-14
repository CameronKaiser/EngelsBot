import os
import json
import asyncio
from time import time

import Configuration

from functools import partial
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class GoogleApi:
    def __init__(self, credential):
        credential_json = json.loads(credential)
        self.credentials = Credentials.from_authorized_user_info(credential_json)
        self.api          = build("calendar", "v3", credentials=self.credentials)
        self.CALENDAR_ID  = Configuration.GOOGLE_CALENDAR_ID
        self.RATE_LIMIT   = 10
        self.WINDOW_LIMIT = 1
        self.window_start = time()
        self.counter      = 0

    async def arbitrate_rate(self):
        if time() - self.window_start > self.WINDOW_LIMIT:
            self.counter = 0
            self.window_start = time()
        elif self.counter >= self.RATE_LIMIT:
            window_elapsed = time() - self.window_start
            await asyncio.sleep(self.WINDOW_LIMIT - window_elapsed)
            self.window_start = time()
            self.counter = 0

    async def _run(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            partial(func, *args, **kwargs)
        )

    async def create_event(self, event):

        await self.arbitrate_rate()

        payload = self.convert_solidarity_event(event)

        request = self.api.events().insert(
            calendarId = self.CALENDAR_ID,
            body       = payload
        )

        print(event)

        self.counter += 1

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

    async def convert_solidarity_event(self, event):
        payload = {}

        event_sessions = payload.get('event_sessions')

        if not event_sessions:
            return None

        main_session = event_sessions[0]

        payload['summary']     = f"TEST - {event.get('title')}"
        payload['description'] = event.get('description')
        payload['start'  ]     = {'dateTime': main_session['start_time']}
        payload['end'    ]     = {'dateTime': main_session['end_time'  ]}

        payload['location'] = main_session.get('location_address')

        return payload

