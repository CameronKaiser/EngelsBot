import os
import json
import asyncio
from datetime import datetime, timedelta
from time import time

import Configuration

from functools import partial
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from Models import GoogleEvent


class GoogleApi:
    def __init__(self, credential):
        credential_json    = json.loads(credential)
        self.credentials   = Credentials.from_authorized_user_info(credential_json)
        self.api           = build("calendar", "v3", credentials=self.credentials)
        self.CALENDAR_ID   = Configuration.GOOGLE_CALENDAR_ID
        self.RATE_LIMIT    = 10
        self.WINDOW_LIMIT  =  1
        self.window_start  = time()
        self.counter       =  0
        self.cached_events = {}

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
        await self.arbitrate_rate()

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(func, *args, **kwargs)
        )

        self.counter += 1

        return response

    async def get_events(self):

        temporary_events = {}

        calendar_ids = []
        finished     = False
        page_token   = None
        while not finished:

            request  = self.api.calendarList().list(pageToken=page_token)
            response = await self._run(request.execute)

            for calendar in response.get("items"):
                if calendar["id"] == Configuration.GOOGLE_CALENDAR_ID:  # Currently only operates on Engels' personal calendar
                    calendar_ids.append(calendar["id"])

            page_token = response.get("nextPageToken")
            if not page_token:
                finished = True

        now  = (datetime.now() - timedelta(days= 64)).astimezone().isoformat()
        then = (datetime.now() + timedelta(days=185)).astimezone().isoformat()

        for calendar_id in calendar_ids:

            finished = False
            page_token = None
            while not finished:

                request = self.api.events().list(
                    calendarId   = calendar_id,
                    timeMin      = now,
                    timeMax      = then,
                    singleEvents = True,
                    orderBy      = "startTime",
                    pageToken    = page_token,
                    showDeleted  = True
                )
                response = await self._run(request.execute)

                retrieved_events = response.get("items")
                for retrieved_event in retrieved_events:
                    temporary_events[retrieved_event['id']] = GoogleEvent(retrieved_event, calendar_id)

                page_token = response.get("nextPageToken")
                if not page_token:
                    finished = True

        self.cached_events = temporary_events
        print(f'Cached {len(self.cached_events)} events from Google Calendar!')

    async def create_event(self, payload):

        request = self.api.events().insert(
            calendarId = self.CALENDAR_ID,
            body       = payload
        )

        return await self._run(request.execute)

    async def update_event(self, payload):

        request = self.api.events().patch(
            calendarId = self.CALENDAR_ID,
            eventId    = payload.get('id'),
            body       = payload
        )

        return await self._run(request.execute)

    async def delete_event(self, event):

        request = self.api.events().delete(
            calendarId  =  event.calendar_id,
            eventId     =  event.id,
            sendUpdates = 'none'
        )

        return await self._run(request.execute)

