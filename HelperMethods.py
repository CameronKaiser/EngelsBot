# Standard Library
import asyncio
import datetime

# Third Party
import cv2
import streamlink

import Configuration
# Local Module
import Mutables
import Configuration as C

# Easy Access
from Configuration import (ROLES, GUILD_ID, REGISTRIES, BRANCHES, Branch)

def is_admin(roles):
    for role in roles:
        if role in ROLES.ADMIN_LIST:
            return True

    return False

async def start_cooldown():
    Mutables.cooldown = True
    await asyncio.sleep(900) # 15 minutes
    Mutables.cooldown = False

def prepare_response(response):
    response_chunks = []

    if len(response) > 2000:
        lines = response.split('\n')
        buffer = ''
        for line in lines:
            if len(buffer) + len(line) + 1 > 2000:
                response_chunks.append(buffer)
                buffer = ''

            buffer += line + '\n'

        if buffer.strip():
            response_chunks.append(buffer)

    else:
        response_chunks.append(response)

    return response_chunks

async def get_predefined_objects(client):
    C.GUILD = client.get_guild(GUILD_ID)

    for registry in REGISTRIES:
        object_type = registry._object_type
        print(f'Getting pre-defined {object_type}s...', end='')
        objects_processed = await registry.hydrate(client)

        print(f' done! ({len(objects_processed.successes)} {object_type}s successfully grabbed)', end='')
        if objects_processed.failures:
            print(
                f' | FAILURES: the following {object_type}s could not be found. '
                f'Ensure the ID is correct and the bot has access to them - {objects_processed.failures}', end='')

        print()

async def get_branches(client):
    for branch in BRANCHES:
        branch_data = BRANCHES[branch]
        try:
            BRANCHES[branch] = Branch(branch_data, client)

            print(f"Branch {branch_data['name']} successfully retrieved.")
        except Exception as error:
            print(f"Could not retrieve branch {branch_data['name']} - {error}")

async def update_events(client):
    try:
        await client.google_api    .get_events()
        await client.solidarity_api.get_events()
    except Exception as error:
        return f"Encountered error during event retrieval - deferring action so as to preserve calendar: {error}"

    engels_id = '15c2778ff1500632209a3609f5dea164325b8db50375c24ebea8e22e3ab8dca8@group.calendar.google.com'

    updated  = 0
    added    = 0
    deleted  = 0

    solidarity_events = client.solidarity_api.cached_events
    google_events     = client.google_api    .cached_events

    for solidarity_event_id, solidarity_event in solidarity_events.items():

        if solidarity_event_id in google_events:
            google_event = google_events[solidarity_event_id]
            if not solidarity_event == google_event:
                response = await client.google_api.update_event(solidarity_event.payload)
                print(f"Event updated: {response}")
                updated += 1
        else:
            print(solidarity_event.payload)
            response = await client.google_api.create_event(solidarity_event.payload)
            print(f"Event added: {response}")
            added += 1

    for google_event_id, google_event in google_events.items():
        if google_event_id not in solidarity_events and google_event.calendar_id == C.GOOGLE_CALENDAR_ID and google_event.status != 'cancelled':
            response = await client.google_api.delete_event(google_event)
            print(f"Deleted google event {google_event_id} from Engels' Calendar as it was not found in Solidarity Tech: {response}")
            deleted += 1

    diagnostics = f'Calendar events synced! ({added} added, {updated} updated, {deleted} deleted)'
    print(diagnostics)
    return diagnostics

def grab_square_image():
    url = C.SQUARE_STREAM_URL  # Replace with actual ID
    streams = streamlink.streams(url)
    best_stream_url = streams["best"].url

    cap = cv2.VideoCapture(best_stream_url)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(f"{C.IMAGE_FILE_PATH}square.jpg", frame)
        cap.release()
    else:
        cap.release()
        raise Exception

def generate_spam_warning(message):

    return f'Class traitor detected: {message.author.mention}\n'                                                    \
           f'Location: {message.jump_url}\n'                                                                         \
           f'Recommended action: Gulag\n\n'                                                                           \
           f'{ROLES.MODERATOR.mention if ROLES.ADMIN not in message.author.roles else "(omitting ping for test)"}\n'   \
           f'{ROLES.ADMIN    .mention if ROLES.ADMIN not in message.author.roles else "(omitting ping for test)"}'

def tableize(array):

#   Get alignment of each column
    left_alignments = []
    for column in array[-1]:
        try:
            float(column.replace('%', '').replace('$', ''))
        except ValueError:
            left_alignments.append(True)
        else:
            left_alignments.append(False)

#   Iterate through transposed 2D array to retrieve max length of each column
    max_lengths = []
    for column in zip(*array):
        max_length = 0
        for value in column:
            max_length = max(max_length, len(value))

        max_lengths.append(max_length)

    table = '```'
    first_row = True
    for row in array:
        table += '\n' if not first_row else ''
        for j in range(len(row)):
            left_alignment = True if first_row else left_alignments[j]
            if left_alignment:
                table += row[j] + ' ' * (max_lengths[j] - len(row[j]))
            else:
                table += ' ' * (max_lengths[j] - len(row[j])) + row[j]

            table += ' ' if j != len(row) - 1 else ''

        first_row = False

    table += '```'

    return table

async def create_forum_digest(client, channel_to_post):
    start_date = datetime.datetime.now() - datetime.timedelta(weeks=1)
    threads    = {}

    for channel in C.GUILD.text_channels:

        if channel.category not in C.CATEGORIES.ORGANIZATIONAL:
            continue

        async for thread in channel.archived_threads(limit=None):
            if not thread.permissions_for(ROLES.DSA_MEMBER).read_messages:
                continue

            messages = 0
            async for message in thread.history(after=start_date, limit=None):
                messages += 1

            threads[thread] = messages


    for thread in C.GUILD.threads:
        if not thread.permissions_for(ROLES.DSA_MEMBER).read_messages or thread.category not in C.CATEGORIES.ORGANIZATIONAL:
            continue

        messages = 0
        async for message in thread.history(after=start_date, limit=None):
            messages += 1

        if threads.get(thread):
            threads[thread] += messages
        else:
            threads[thread]  = messages

    response = f"## Weekly Forum Digest\n" \
               f"Here are the most active threads / forum posts you may have missed this week!"

    sorted_threads = sorted(threads.items(), key=lambda x: x[1], reverse=True)

    i = 1
    for thread, count in sorted_threads:
        response += f'\n{i}. {thread.mention} - {count} messages'

        if i == 10:
            break

        i += 1

    await channel_to_post.send(response)