# Standard Library
import asyncio
import random
import aiohttp
import urllib.parse
from   datetime import date
from   time     import time

import discord

import Configuration
import HelperMethods
from   Models import (Endpoint, Response, SolidarityUser)

# Easy Access
from Configuration import CHANNELS, MEMBERS, ROLES, MESSAGES, EMOJIS, BRANCHES

class SolidarityAPI:

    RETRY_ATTEMPTS = 3

    GET_USERS_ENDPOINT   = Endpoint('https://api.solidarity.tech/v1/users' , 'GET')
    UPDATE_USER_ENDPOINT = Endpoint('https://api.solidarity.tech/v1/users/', 'PUT')

    def __init__(self, token):
        self.token        = token
        self.rate_limiter = self.RateLimiter()
        self.session      = aiohttp.ClientSession()
        self.cached_users = {}

#   actual endpoint stuff

    async def get_users(self):

        finished = False
        offset = 0
        while not finished:
            response = await self._execute_request(self.GET_USERS_ENDPOINT, query=f'?_limit=100&_offset={offset}') # 100 appears to be the max the api allows

            if response:
                json = response.json

                for user in json['data']:
                    self.cached_users[user['email']] = SolidarityUser(user)

                offset += 100

                if offset + 100 >= json['meta']['total_count']:
                    finished = True

            else:
                finished = True

        print(f'Cached {len(self.cached_users)} users from Solidarity Tech!')

    async def get_user(self, query=''):
        response = await self._execute_request(self.GET_USERS_ENDPOINT, query=query)

        user = None
        if response:
            payload = response.json
            if payload.get('data'):
                user = SolidarityUser(payload.get('data')[0])

        return user

    async def update_user(self, user_id, payload):
        response = await self._execute_request(self.UPDATE_USER_ENDPOINT, query=user_id, payload=payload)

        return response

    async def _execute_request(self, endpoint, query='', payload=None):

        error_message = 'Unknown'

        for attempt in range(self.RETRY_ATTEMPTS):

            await self.rate_limiter.adjudicate()

            try:

                async with self.session.request(
                    url     = endpoint.url + urllib.parse.quote_plus(str(query), safe=':/?=&'),
                    headers = {'Authorization': f'Bearer {self.token}'},
                    method  = endpoint.method                                                              ,
                    json    = payload
                ) as response:

                    try:
                        json = await response.json()
                    except Exception:
                        json = None

                    static_response = Response(
                        status  = response.status       ,
                        url     = endpoint.url          ,
                        headers = dict(response.headers),
                        json    = json
                    )

                    assessment = await self._assess_response(static_response)

                    if assessment == 'success':
                        return static_response

                    if assessment == 'failure':
                        await self._log_failure(endpoint.url, static_response.status, json)
                        return None

                    if json:
                        error_message = json

            except Exception as error:
               error_message = error

            print(f'Call to Solidarity API URL {endpoint.url} failed - retrying in {3**attempt} seconds')
            await asyncio.sleep(3**attempt)

        await CHANNELS.BOT_TESTING.send(f'Call to Solidarity API URL {endpoint.url}{query} ({endpoint.method}) failed after {self.RETRY_ATTEMPTS} times - aborting. Error: {error_message}')
        return None

    @staticmethod
    async def _log_failure(url, status_code, json):
        log = f'Call to Solidarity API URL {url} failed with error code {status_code}'

        if json and 'errors' in json:
            log   += f' and the following errors: {json.get("errors")}'

        await CHANNELS.BOT_TESTING.send(log)

    async def _assess_response(self, response):

        if response.ok:
            self.rate_limiter.counter += 1
            return 'success'

        status_code = response.status

        if 500 <= status_code < 600:
            return 'retry'

        if status_code == 429:
        #   Rate Limited
            await self.rate_limiter.initiate_throttle_response(response)
            return 'retry'

        return 'failure'

    class RateLimiter:

        RATE_COUNTER_LIMIT = 60
        RATE_LIMIT         = 30 # Seconds

        def __init__(self):
            self.counter        = 0
            self.window_start   = time()
            self._lock          = asyncio.Lock()
            self.throttle_event = None

        def _reset_window(self):
            self.counter      = 0
            self.window_start = time()

        async def adjudicate(self):
            async with self._lock:
                if self.throttle_event:
                    await self.throttle_event.wait()
                    return

                if self.counter >= self.RATE_COUNTER_LIMIT:
                    window_elapsed = time() - self.window_start
                    if window_elapsed < self.RATE_LIMIT:
                        self.throttle_event = ThrottleEvent(self.RATE_LIMIT - window_elapsed)
                        await self.throttle_event.wait()
                        self.throttle_event = None

                    self._reset_window()

        async def initiate_throttle_response(self, response):
            async with self._lock:
                if not self.throttle_event:
                    self.throttle_event = ThrottleEvent(response.headers['Retry-After'])

            #   Wait outside the lock so we can let others through and not start a loop of locking
            await self.throttle_event.wait()

            async with self._lock:
                if self.throttle_event:
                    self.throttle_event = None
                    self._reset_window()




class ThrottleEvent:

    def __init__(self, seconds_throttled):
        self.seconds_throttled   = seconds_throttled
        self.throttle_start_time = time()

    async def wait(self):
        await asyncio.sleep(self.seconds_throttled - (time() - self.throttle_start_time))

class VerifyButton(discord.ui.View):
    def __init__(self):
    #   We have to initialize the button and add the emoji after in the constructor otherwise it seems to initialize asychronously which means it
    #   happens before the EMOJIS class is hydrated, meaning it tries to inject an int, which fails. Time travel I guess, I don't know
        super().__init__(timeout=None)
        button = self.create
        button.emoji = EMOJIS.ROSA or '✔️'

    @discord.ui.button(label="Verify membership & access the server!", style=discord.ButtonStyle.red, custom_id='verify_button_new')
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ROLES.DSA_MEMBER in interaction.user.roles and not HelperMethods.is_admin(interaction.user.roles):
            await interaction.response.send_message(
                content   = f"You're all good - already verified!",
                ephemeral = True)
            return

        if HelperMethods.is_admin(interaction.user.roles):
            await interaction.response.send_message(
                'Optional Admin Override: Select another member to verify on behalf of',
                view      = SelectMember(interaction.user, interaction.client),
                ephemeral = True)
        else:
            await interaction.response.send_modal(VerificationModal(interaction.user, interaction.client))

class SelectMember(discord.ui.View):
    def __init__(self, user, client):
        super().__init__(timeout=60)
        self.user   = user
        self.client = client

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="User you want to verify", min_values=0, max_values=1)
    async def select_member(self, interaction, select):
        member = select.values[0] if select.values else None
        await interaction.response.send_modal(VerificationModal(interaction.user, interaction.client, member_override=member))

    @discord.ui.button(label="Skip user override (verify myself)", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction, button):
        await interaction.response.send_modal(VerificationModal(interaction.user, interaction.client))

class VerificationModal(discord.ui.Modal, title="Are you a DSA Member? Let's get you verified!"):
    def __init__(self, user, client, member_override=None):
        super().__init__()
        self.user            = user
        self.client          = client
        self.member_override = member_override

    user_email = discord.ui.TextInput(
        label="Please enter your email",
        placeholder='example@socodsa.org',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )

    user_zipcode = discord.ui.TextInput(
        label="Please enter your zipcode",
        placeholder='12345',
        style=discord.TextStyle.short,
        required=True,
        max_length=5
    )

    user_name = discord.ui.TextInput(
        label="Please enter your preferred name",
        style=discord.TextStyle.short,
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):

        if self.member_override:
            user = self.member_override
        else:
            user = interaction.user

        try:

            input_email   = self.user_email  .value
            input_zipcode = self.user_zipcode.value
            input_name    = self.user_name   .value

            solidarity_user = self.client.solidarity_api.cached_users.get(input_email)

            if not solidarity_user:
                solidarity_user = await self.client.solidarity_api.get_user(query=f'?email={input_email}')

            if not solidarity_user or (solidarity_user.data['address']['zip_code'] and solidarity_user.data['address']['zip_code'][:5] != input_zipcode):
                await interaction.response.send_message(
                    content   = f"Sorry, we couldn't find a user matching email {input_email} and zipcode {input_zipcode} in our records. If you believe this to be an error, please open a ticket with the Steering Committee [here]({MESSAGES.STEERING_TICKET.jump_url})\n\nNote: If you signed up to be a member within the past 4 hours, please try again later - it can take some time for the profile to be finalized in our system!",
                    ephemeral = True)
                return

            if not solidarity_user.data['custom_user_properties']['membership-status']:
                await interaction.response.send_message(
                    content=f"It looks like you're not a member yet! Membership starts with DSA National and then automatically connects to us here at Sonoma County DSA. Take a minute to [sign up right now](https://act.dsausa.org/donate/membership/?source=sonoma-county-discord)!\n\nIf you believe this to be an error, please open a ticket with the Steering Committee [here]({MESSAGES.STEERING_TICKET.jump_url})\n\nNote: If you signed up to be a member within the past 4 hours, please try again later - it can take some time for the profile to be finalized in our system! Additionally, if you signed up with a dues waiver, it may take up to a week to register in our system.",
                    ephemeral=True)
                return


            if solidarity_user.data['custom_user_properties']['membership-status'][0]['value'] != 'AfVqfj0n':
                await interaction.response.send_message(
                    content   = f"We've got you in our records, but it looks like your membership dues have expired. If you re-enable your membership with National, we can get you back in!",
                    ephemeral = True)
                return

            branch = BRANCHES.get(solidarity_user.data['chapter_id'])
            if HelperMethods.is_admin(user.roles):
                print(f'Skipping verification role edits for user {user.name}, as user role is too elevated to modify')
            else:
                updated_roles = set(user.roles)
                updated_roles.discard(ROLES.DSA_CURIOUS)
                updated_roles.add    (ROLES.DSA_MEMBER)

                if branch:
                    print(f'User {user.name} in branch - adding role {branch.role.name}')
                    updated_roles.add(branch.role)

                await user.edit(
                    nick   = f'{input_name} ({user.name})',
                    roles  = list(updated_roles),
                    reason = 'Member verified via EngelsBot'
                )

        #   Confirm member and announce their arrival in DSA Chatting
            try:
                message = f"Thank you {input_name}, you're verified! You now have access to the main channels we use to organize, which you'll find in the sidebar on the left."
                if CHANNELS.COMMITTEE_SIGNUP:
                    message += f" You now have access to all organization channels except those of committees - if you're interested in joining any, please see {CHANNELS.COMMITTEE_SIGNUP.mention}!"

                await interaction.response.send_message(
                    content   = message,
                    ephemeral = True)

                await CHANNELS.DSA_CHATTING.send(random.choice(Configuration.WELCOME_MESSAGES).replace("{user}", user.mention))
                await CHANNELS.DSA_CHATTING.send(random.choice(Configuration.WELCOME_GIFS))

            except Exception as error:
                await CHANNELS.BOT_TESTING.send(f'Unable to announce user verification - check your DSA_CHATTING id in Configuration ({error})')

        #   Attempt to update the user in Solidarity Tech
            try:
                custom_properties = solidarity_user.data.get('custom_user_properties')
                payload = {'custom_user_properties': {}}
                payload['custom_user_properties']['date-verified-in-discord'] = str(date.today())
                if custom_properties.get('discord-handle') is None:
                    payload['custom_user_properties']['discord-handle'] = user.name

                updated_user = await self.client.solidarity_api.update_user(solidarity_user.data['id'], payload)

                date_joined  = 'Unretrievable'
                ydsa_chapter = 'None'
                branch_name  = 'None' if not branch else branch.name
                if custom_properties:
                    if custom_properties.get('join-date'):
                        date_joined = custom_properties['join-date']

                    if custom_properties.get('ydsa-chapter'):
                        ydsa_chapter = custom_properties['ydsa-chapter']

                updated = "✅ User handle successfully updated in Solidarity Tech" if updated_user else "❌ Failed to update user handle in Solidarity Tech"

                embed = discord.Embed(
                    title=f"Member verified ({user.name})",
                    description=f'- **User**: {user.mention}\n'
                                f'- **Joined DSA**: {date_joined}\n'
                                f'- **YDSA Chapter**: {ydsa_chapter}\n'
                                f'- **Branch**: {branch_name}\n'
                                f'{updated}',
                    color=MEMBERS.ENGELS_BOT.color
                )

                await CHANNELS.AUTO_MOD.send(embed=embed)

            except Exception as error:
                await CHANNELS.BOT_TESTING.send(f"‼️ Failed to update {user.mention} in Solidarity Tech: {error}")

        except Exception as error:
            await CHANNELS.BOT_TESTING.send(f'‼️ User {user.mention}s verification failed: {error}')
            await interaction.response.send_message(
                content   = f"We're sorry, an error occurred and we were unable to complete verification. A log has been sent to the admin team and we will try to fix this ASAP! In the meantime, feel free to verify manually by [opening a ticket with Steering Committee]({MESSAGES.STEERING_TICKET.jump_url}).",
                ephemeral = True)











