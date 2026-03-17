# Standard Library
import asyncio

# Third Party
import cv2
import streamlink

# Local Module
import Mutables
import Configuration as C

# Easy Access
from Configuration import (ROLES, GUILD_ID, REGISTRIES)

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

    return f'Class traitor detected: {message.author.mention}\n' \
           f'Location: {message.jump_url}\n'                     \
           f'Recommended action: Gulag\n\n'                      \
           f'{ROLES.MODERATOR.mention}\n'                                \
           f'{ROLES.ADMIN    .mention}'

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