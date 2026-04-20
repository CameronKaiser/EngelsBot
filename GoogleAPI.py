import os
import json
import asyncio
from datetime import datetime, timedelta
from time import time

import Configuration

from functools import partial
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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

        events = {}

        calendar_ids = []
        finished = False
        page_token = None
        while not finished:

            request  = self.api.calendarList().list(pageToken=page_token)
            response = await self._run(request.execute)
            print(f"CALENDAR LIST: {response}")

            for calendar in response.get("items"):
                calendar_ids.append(calendar["id"])

            page_token = response.get("nextPageToken")
            if not page_token:
                finished = True

        now  = datetime.now().astimezone().isoformat()
        then = (datetime.now() + timedelta(days=31)).astimezone().isoformat()

        print(now)

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
                    pageToken    = page_token
                )
                response = await self._run(request.execute)

                print(f"RETRIEVED EVENTS: {response}")

                retrieved_events = response.get("items")
                for retrieved_event in retrieved_events:
                    events[retrieved_event['id']] = retrieved_event

                page_token = response.get("nextPageToken")
                if not page_token:
                    finished = True

        print(f'Cached {len(self.cached_events)} events from Google Calendar!')

    async def create_event(self, payload):

        request = self.api.events().insert(
            calendarId = self.CALENDAR_ID,
            body       = payload
        )

        print(f'payload: {payload}')

        return await self._run(request.execute)

    async def delete_event(self, calendar_id: str, event_id: str):
        request = self.api.events().delete(
            calendarId=calendar_id,
            eventId=event_id)
        return await self._run(request.execute)

    async def update_event(self, calendar_id: str, event_id: str, event_body: dict):
        async with self.rate_limiter:
            request = self.api.events().update(
                calendarId =calendar_id,
                eventId=event_id,
                body=event_body
            )
            return await self._run(request.execute)

    def generate_event_payloads(self):

        payloads = {}

        for event_id in self.cached_events:
            event = self.cached_events[event_id]
            payload = {}
            payload['id'         ] = event    [    'id'     ]
            payload['summary'    ] = event.get('summary'    )
            payload['description'] = event.get('description')
            payload['start'      ] = event.get('start'      )
            payload['end'        ] = event.get('end'        )
            payload['location'   ] = event.get('location'   )

            payloads[event['id']] = payload

        return payloads

