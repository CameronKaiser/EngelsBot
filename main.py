# Standard library
import asyncio
import datetime
import random
import statistics

# Third party
import numpy as np
import discord
import discord.ext

# Local Modules
import Configuration as C
import Airtable
import HelperMethods
import Objects
import RecruitmentDrive
import Ticket
import Mutables

# Easy Access
from HelperMethods import is_admin
from Configuration import (DISCORD_API_KEY, CATEGORIES, CHANNELS, ROLES, MEMBERS, MESSAGES, EMOJIS, GUILD_ID, REGEX)
from Objects import Member, Quote

intents                 = discord.Intents.default()
intents.message_content = True
intents.members         = True
intents.reactions       = True
intents.dm_reactions    = True

client = discord.Client(intents=intents)
tree   = discord.app_commands.CommandTree(client)

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#    ~ Initialization ~
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

    client.loop.create_task(Airtable.get_quotes())

    await HelperMethods.get_predefined_objects(client)

    client.add_view(Ticket.CreateTicketButton())
    client.add_view(Ticket.CloseTicketButton())

    if CHANNELS.DSA_CHATTING:
        client.loop.create_task(random_thought(CHANNELS.DSA_CHATTING))

    await CHANNELS.BOT_TESTING.send("Engels Online")

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#    ~ Cron Jobs ~
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

async def random_thought(channel):
    while True:
        delay   = random.randint(C.ENGELS_PONTIFICATE_MIN_DELAY, C.ENGELS_PONTIFICATE_MAX_DELAY)
        await asyncio.sleep(delay)
        message = await channel.send(random.choice(C.PROFOUND_STATEMENTS))

        Mutables.thoughtful_messages.add(message.id)

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#    ~ Webhooks ~
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

@client.event
async def on_message_delete(message):

    if message.channel == CHANNELS.AUTO_MOD or message.channel == CHANNELS.CALENDAR:
        return

    embed = discord.Embed(
        title       = "Message Deleted",
        description =  message.content or "(attachment only)",
        color       =  discord.Color.red()
    )
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    embed.add_field(name="Channel", value=message.channel.mention)

#   Steering related messages shall be sent to the Steering channel rather than the moderator channel for confidentiality
    if message.channel.category == CATEGORIES.STEERING_COMMITTEE or message.channel.category == CATEGORIES.TICKETS:
        channel = CHANNELS.STEERING_COMMITTEE
    else:
        channel = CHANNELS.AUTO_MOD

    await channel.send(embed=embed)

    if message.attachments:
        files = [await a.to_file() for a in message.attachments]
        await channel.send(files=files)

        close_embed = discord.Embed(
            title = "Message's attachments included above",
            color =  discord.Color.red()
        )

        await channel.send(embed=close_embed)

    if message.embeds:
        await channel.send(embeds=message.embeds)

        close_embed = discord.Embed(
            title = "Message's embeds included above",
            color =  discord.Color.red()
        )

        await channel.send(embed=close_embed)

@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    # If cached_message exists, on_message_delete already handled it
    if payload.cached_message:
        return

    if payload.channel_id == CHANNELS.AUTO_MOD.id or payload.channel_id == CHANNELS.CALENDAR.id:
        return

    embed = discord.Embed(
        title       =  "Message Deleted (uncached - cannot get information)",
        description = f"Message ID: `{payload.message_id}`",
        color       =   discord.Color.orange()
    )
    embed.add_field(name="Channel", value=f"<#{payload.channel_id}>")

    await CHANNELS.AUTO_MOD.send(embed=embed)

@client.event
async def on_raw_reaction_add(payload):

    emoji = payload.emoji
    user  = payload.member

    if user.bot:
        return

    if str(emoji) == '💬':
        channel = await C.GUILD.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if message.content and not message.author.bot:

            if any(quote.message_id == message.id for quote in Mutables.quote_cache.values()):
                return

            await message.add_reaction("💬")

            quote = Airtable.upload_quote(message.content, message.author.id, message.id, message.jump_url)
            quote_number = int(quote['fields']['Number'])

            Mutables.quote_cache[quote_number] = Quote(message.content, quote_number, int(message.author.id), message.jump_url, quote['id'], message.id)
            print(f"Added quote {quote['fields']['Number']} to cache ({message.id})")

            await channel.send(f"Quote #{quote['fields']['Number']} has been added by {user.mention}: [({message.id})]({message.jump_url})")

    if MESSAGES.COMMITTEE_SIGNUP is not None and payload.message_id == MESSAGES.COMMITTEE_SIGNUP.id:
    #   Committee Reaction
        print(f'{user.name} has reacted to the Committee signup message with {emoji}')

        chosenCommittee = None
        currentRoles    = []
        for role in user.roles:
            currentRoles.append(role.name)

        for committee in C.COMMITTEES:
            if committee.emoji == str(emoji):
                if committee.role in currentRoles or user.name in committee.requested_members:
                #   Duplicate request - ignore
                    print(f'{user.name} has sent a duplicate request. Ignoring')
                    return

                chosenCommittee = committee
                committee.requested_members.append(user.name)
                break

        if chosenCommittee:
            await CHANNELS.AUTO_MOD.send(f'{user.mention} has issued a request to join the {chosenCommittee.name} Committee {emoji}!')
        else:
            print(f'Removing extraneous react: {emoji}')
            await MESSAGES.COMMITTEE_SIGNUP.remove_reaction(emoji, user)

        return

    if MESSAGES.ROLE_SIGNUP is not None and payload.message_id == MESSAGES.ROLE_SIGNUP.id:
    #   Role Reaction
        print(f'{user.name} has reacted to the Role selection message with {emoji}')

        social_roles = C.SOCIAL_ROLES

        role_chosen = social_roles[str(emoji)]
        if not role_chosen:
            await MESSAGES.ROLE_SIGNUP.remove_reaction(emoji, user)
            return

        dsa_member = False
        for role in user.roles:
            if role.name == 'DSA Member':
                dsa_member = True
                break

        if not dsa_member:
            return

        if role_chosen:
            for role in social_roles:
                if role != str(emoji):
                    await MESSAGES.ROLE_SIGNUP.remove_reaction(role, user)

            role_to_add = C.GUILD.get_role(social_roles[str(emoji)])

            await user.add_roles(role_to_add)

        return

    return

@client.event
async def on_raw_reaction_remove(payload):

    user = C.GUILD.get_member(payload.user_id)
    if user is None:
        user = await C.GUILD.fetch_member(payload.user_id)
    emoji = payload.emoji

    if MESSAGES.ROLE_SIGNUP is not None and payload.message_id == MESSAGES.ROLE_SIGNUP.id:
    #   Role Reaction
        print(f'{user.name} has unreacted to the Role selection message with {emoji}')

        role_id = C.SOCIAL_ROLES[str(emoji)]
        if role_id:
            role = C.GUILD.get_role(role_id)
            await user.remove_roles(role)

    return

# Automatically follows all users to a thread. Note: may not work - we may need to make a post and edit pings into it, rather than use no_ping
@client.event
async def on_thread_create(thread):
    no_ping = discord.AllowedMentions(users=False, roles=False, everyone=False)

    await asyncio.sleep(3)
    if thread.parent == CHANNELS.PERSONAL_REQUESTS:
        message = await thread.send(f'Engels is ensuring this thread is visible to everyone: \n\n'
                                    f'{ROLES.DSA_MEMBER.mention}\n'
                                    f'{ROLES.CURIOUS   .mention}\n'
                                    f'{ROLES.COMRADE   .mention}', allowed_mentions=no_ping)
        await asyncio.sleep(3)
        await message.delete()

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#    ~ Slash Commands ~
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

@tree.command(name="sync_commands", description="Syncs commands to the server", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction):
    if not is_admin(interaction.user.roles):
        await interaction.response.send_message('sorry boss, admin only') # type: ignore
        return

    await tree.sync(guild=discord.Object(id=GUILD_ID))
    await interaction.response.send_message('Commands Synced!') # type: ignore

@tree.command(name="get_channel_leaderboard", description="Gets statistics on channels. Don't spam this", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction, months: int):
    if not HelperMethods.is_admin(interaction.user.roles):
        await interaction.response.send_message("sorry boss, that's for admins only") # type: ignore
        return

    if months > 12 or months < 1:
        await interaction.response.send_message("Please choose a number of months from 1-12") # type: ignore
        return

    await interaction.response.defer() # type: ignore

    start_date = datetime.datetime.now() - datetime.timedelta(days=months * 31)
    channels   = {}

    for channel in C.GUILD.text_channels:

        if channel.category == CATEGORIES.ARCHIVED:
            continue

        messages = 0
        async for message in channel.history(after=start_date, limit=None):
            messages += 1

        channels[channel] = messages

        thread_messages = 0
        async for thread in channel.archived_threads(limit=None):
            async for message in thread.history(after=start_date, limit=None):
                thread_messages += 1

        channels[channel] += thread_messages

    for thread in C.GUILD.threads:
        channel = thread.parent

        if channel.category == CATEGORIES.ARCHIVED:
            continue

        messages = 0
        async for message in thread.history(after=start_date, limit=None):
            messages += 1

        if channels.get(channel):
            channels[channel] += messages
        else:
            channels[channel] = messages

    response = f"## Channels ranked by number of messages (past {months} months)\n"

    sorted_channels = sorted(channels.items(), key=lambda x: x[1], reverse=True)
    i = 1
    for channel, count in sorted_channels:
        response += f'{i}. {channel.mention}: {count}\n'
        i += 1

    response_chunks = HelperMethods.prepare_response(response)

    for response in response_chunks:
        await CHANNELS.BOT_TESTING.send(response)

    await interaction.followup.send(f'Analytics have been sent to {CHANNELS.BOT_TESTING.mention}. Users will only be able to see channel names of those '
                                    f'they have access to - feel free to forward wherever.')

@tree.command(name="spawn_ticket_system", description="Spawns a ticket requesting system in the channel input", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction, channel_id: str):
    if not is_admin(interaction.user.roles):
        await interaction.response.send_message("sorry boss, that's for admins only") # type: ignore
        return

    try:
        embed = discord.Embed(
            title       = "Steering Committee Ticket System",
            description = C.STEERING_TICKET_DESCRIPTION,
            color       = discord.Color.blue()
        )

        channel = await client.fetch_channel(int(channel_id))
        message = await channel.send(embed=embed, view=Ticket.CreateTicketButton())
        await interaction.response.send_message(f'Ticket System generated at: {message.jump_url}') # type: ignore

    except Exception as e:
        await interaction.response.send_message(f'shit borked idk, prolly add a proper channel ID ({e})') # type: ignore

@tree.command(name="sync_airtable", description="Updates the members airtable with current information", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction):
    if not is_admin(interaction.user.roles):
        await interaction.response.send_message("sorry boss, that's for admins only") # type: ignore
        return

    await interaction.response.defer() # type: ignore

    try:
        members = {}

        server = interaction.guild
        for member in server.members:
            members[member.name] = Member(member)

        await asyncio.to_thread(Airtable.update_members_table, members)

        await interaction.followup.send('Airtable synced!')

    except Exception as e:
        await interaction.response.send_message(f'shit borked idk ({e})') # type: ignore

@tree.command(name="sync_airtable_analytics", description="Heavy data crunching. Don't spam this", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction):
    if not is_admin(interaction.user.roles):
        await interaction.response.send_message("sorry boss, that's for admins only") # type: ignore
        return

    await interaction.response.defer() # type: ignore

    try:
        members = {}

        for member in C.GUILD.members:
            members[member.name] = Member(member)

        last_month = datetime.datetime.now() - datetime.timedelta(days=31)
        total_messages = 0
        for channel in C.GUILD.text_channels:
            async for message in channel.history(after=last_month, limit=None):
                member = members.get(message.author.name)
                if member:
                    member.message_count += 1

                total_messages += 1

            async for thread in channel.archived_threads(limit=None):
                async for message in thread.history(after=last_month, limit=None):
                    member = members.get(message.author.name)
                    if member:
                        member.message_count += 1

                    total_messages += 1

        for thread in C.GUILD.threads:
            async for message in thread.history(after=last_month, limit=None):
                member = members.get(message.author.name)
                if member:
                    member.message_count += 1

                total_messages += 1

        counts = []
        for member in members:
            member_object = members[member]

            if member_object.message_count > 0:
                counts.append(member_object.message_count)

        median = statistics.median(counts)
        q1, q3 = np.percentile(counts, [25, 75])

        print(f'q1 = {q1} and q3 = {q3}')

        for member in members:
            member_object = members[member]
            message_count = member_object.message_count

            relative_activity_level = None

            if message_count < q1:
                relative_activity_level = 'Low'
            elif message_count < q3:
                relative_activity_level = 'Average'
            else:
                relative_activity_level = 'High'

            member_object.relative_activity_level = relative_activity_level

            activity_level = None

            if message_count == 0:
                activity_level = 'Missing'
            elif message_count < 100:
                activity_level = 'Low'
            elif message_count < 500:
                activity_level = 'Medium'
            else:
                activity_level = 'High'

            member_object.activity_level = activity_level

        Airtable.update_members_table(members)

        await interaction.followup.send('Analytics synced to airtable O_O')

    except Exception as e:
        await interaction.response.send_message(f'shit borked idk ({e})') # type: ignore

@tree.command(name="forumize_category", description="Will convert an entire category into forums. Enter ID of category and name of forum", guild=discord.Object(id=GUILD_ID))
async def slash_command(interaction: discord.Interaction, id: str, name: str):
    if not is_admin(interaction.user.roles):
        await interaction.response.send_message("sorry boss, that's for admins only") # type: ignore
        return

    category = C.GUILD.get_channel(int(id))

    for channel in category.text_channels:
        if channel.topic is None:
            await interaction.response.send_message(f"Please add a topic for all channels in the category ({channel.mention})") # type: ignore
            return

    await interaction.response.defer() # type: ignore

    forum    = await C.GUILD.create_forum(name=name, category=category)
    no_ping  = discord.AllowedMentions(users=False, roles=False, everyone=False)

    try:

        for channel in category.text_channels:
            messages = []

            async for message in channel.history(limit=None):
                member = message.author.display_name
                urls   = []
                for attachment in message.attachments:
                    urls.append(attachment.url)

                message_to_send = f'**{member}**: {message.content}'

                if urls:
                    message_to_send += '\n\n' + '\n'.join(urls)

                messages.append(message_to_send)

            thread, _ = await forum.create_thread(name=channel.name.replace('-', ' ').title(), content=channel.topic)

            message_to_send = ''
            for message in reversed(messages):
                if len(message) + len(message_to_send) > 1998:
                    if len(message_to_send) > 2000:
                        await thread.send(message_to_send[:2000 ], allowed_mentions=no_ping)
                        await thread.send(message_to_send[ 2000:], allowed_mentions=no_ping)
                    else:
                        await thread.send(message_to_send        , allowed_mentions=no_ping)
                    message_to_send = message
                else:
                    message_to_send += f'\n\n{message}'

        #   Catch and send the last message if there is one
            if message_to_send:
                if len(message_to_send) > 2000:
                    await thread.send(message_to_send[:2000], allowed_mentions=no_ping)
                    await thread.send(message_to_send[2000:], allowed_mentions=no_ping)
                else:
                    await thread.send(message_to_send, allowed_mentions=no_ping)

        await interaction.followup.send(f"Category forumized: {forum.mention}")

    except Exception as e:
        await interaction.followup.send_message(f'shit borked idk ({e})') # type: ignore

# -------------------------------------------------------------------------------------------------------------------------------------------------------------
#    ~ Message Interactions ~
# -------------------------------------------------------------------------------------------------------------------------------------------------------------

@client.event
async def on_message(message):

    server = message.guild

    if message.author == MEMBERS.ENGELS_BOT or server is None or server != C.GUILD:
        return

    admin = is_admin(message.author.roles)

    text     = message.content.lower()
    raw_text = message.content

#   We get scam spam all the time. This alerts moderators so they can ban immediately
    spam_score = 0
    for spam_trigger in C.SPAM_TRIGGERS:
        if spam_trigger in text:
            spam_score = spam_score + 1

    if spam_score >= 3:
        await message.add_reaction('🤨')
        await CHANNELS.AUTO_MOD.send(HelperMethods.generate_spam_warning(message))
        return

    if '.quote' in text and message.channel in CHANNELS.QUOTE_PERMITTED:

        quote_request = Objects.QuoteRequest(text)

        if not quote_request.valid:
            await message.channel.send('idk what you mean dawg')
            return

        quote_number = quote_request.number
        if quote_request.delete:
            if not admin:
                await message.channel.send("sorry boss, that's for admins only")  # type: ignore
                return

            if quote_number in Mutables.quote_cache:
                try:
                    Airtable.delete_quote(Mutables.quote_cache[quote_number])
                    await message.channel.send(f'Quote #{quote_number} deleted')

                except Exception:
                    await message.channel.send(f'Unable to delete quote ({Exception})')

                return

            if quote_number:
                await message.channel.send(f'quote #{quote_number} does not exist')

            else:
                await message.channel.send(f'give me a number numbnuts')

            return

        if quote_number:
            quote = Mutables.quote_cache.get(quote_number)
            if not quote:
                await message.channel.send(f'quote #{quote_number} does not exist')
                return
        else:
            if len(Mutables.quote_cache) == 0:
                await message.channel.send('there *are* no quotes!!!')
                return

            quote = random.choice(list(Mutables.quote_cache.values()))

        embed = discord.Embed(
            title       = f"Quote #{quote.number}",
            description = f'{quote.text}\n'
                          f'• <@!{quote.user_id}> [(See Message)]({quote.jump_url})',
            color       = MEMBERS.ENGELS_BOT.color
        )

        await message.channel.send(embed=embed)
        return

#   Grabs a realtime photo of Old Courthouse Square using the livestream (currently broken due to youtube changing URL functionality)
    if ('city square' in text or 'courthouse square' in text or text == 'square' or 'santa rosa square' in text) and len(text) < 30:

        try:
            await asyncio.to_thread(HelperMethods.grab_square_image)

        except Exception as error:
            await message.channel.send(f'stream pull is borked sorry ({error})')
            return

        now  = datetime.datetime.now()
        time = now.strftime("%I:%M%p").lower()

        await message.channel.send(content=f"Santa Rosa Courthouse Square on {now.strftime('%B')} {now.day}, {now.year} ~ {time}", file=discord.File(f'{C.IMAGE_FILE_PATH}square.jpg'))

    if message.reference is not None and message.reference.message_id in Mutables.thoughtful_messages:
        await message.reply(random.choice(C.ENGELS_DISSENT_MEMES))
        Mutables.thoughtful_messages.remove(message.reference.message_id)
        return

    if 'engels choose a random person to ban' in text:
        if message.author == MEMBERS.CALVIN:
            await message.channel.send('i already chose you unc')
        else:
            await message.channel.send(MEMBERS.CALVIN.mention)

    if   'ROSA' in raw_text:
        await message.add_reaction(EMOJIS.ROSA_AGGRO)
    elif 'rosa' in text and not ('santa rosa' in text or 'santarosa' in text):
        await message.add_reaction(EMOJIS.ROSA)

    if text == 'scoreboard' or text == 'leaderboard' :

        results = RecruitmentDrive.Recruitment_Drive_Processor()

        if results.errors:
            await message.channel.send(f'sorry boss the gig is up ({results.errors})')
            return

        content = f'## ➕ Member Increase Leaderboard\n'                          \
                  f'{HelperMethods.tableize(results.absolute_increase_array)}\n'   \
                  f'## 📈 Percent Increase Leaderboard\n'                           \
                  f'{HelperMethods.tableize(results.relative_increase_array)}\n­'

        sonoma_embed = discord.Embed(title=f'{C.CHAPTER_NAME} {EMOJIS.CHAPTER_LOGO}', color=0xff0000)
        sonoma_embed.add_field(name='Member Increase' , value=str(results.chapter_absolute_increase), inline=True)
        sonoma_embed.add_field(name='Percent Increase', value=str(results.chapter_relative_increase), inline=True)

        await message.channel.send(content=content, embed=sonoma_embed)
        return

    if 'capacity meme' in text:
        await message.channel.send(file=discord.File(random.choice(C.CAPACITY_MEMES)))

    if text == 'gulag':
        await message.channel.send(random.choice(C.GULAG_MEMES))

    if 'zohran bad' in text:
        await message.channel.send(file=discord.File(random.choice(C.ZOHRAN_BAD_MEMES)))

    if 'sonoma' in text and 'christi' in text:
        await message.channel.send(file=discord.File(random.choice(C.SONOMA_CHRISTI_MEMES)))

    if 'sonoma' in text and 'georgia' in text:
        await message.channel.send(file=discord.File(random.choice(C.SONOMA_GEORGIA_MEMES)))

    if 'wtf engels'  in text or 'shut up engels' in text or 'stfu engels' in text or 'fuck you engels' in text or 'watch yourself engels' in text or \
       'engels cmon' in text or ('fuck' in text and 'engels' in text) or ('pig' in text and 'engels' in text):
        if message.author == MEMBERS.CALVIN:
            await message.channel.send('okay unc')
        else:
            await message.channel.send(random.choice(C.ENGELS_DISSENT_MEMES))

    if 'just do a revolution' in text or 'just seize the means of production' in text:
        await message.channel.send('https://tenor.com/view/drake-gif-25177956')

    if 'i love dems' in text or 'i love democrats' in text or 'we love the dems' in text:
        await message.channel.send('https://tenor.com/view/stop-it-get-some-help-gif-15058124')

    if REGEX.AI_CHECK.search(text) and REGEX.ART_CHECK.search(text) and not Mutables.cooldown:
        asyncio.create_task(HelperMethods.start_cooldown())
        await message.channel.send('https://tenor.com/view/ah-shit-here-we-go-again-ah-shit-cj-gta-gta-san-andreas-gif-13933485')

    if text == 'stalinism':
        await message.add_reaction('👻')

    if 'clanker' in text:
        await message.add_reaction('😔')

    if 'engels' in text:
        await message.add_reaction('😛')

    if 'avakian' in text:
        await message.channel.send(file=discord.File(f'{C.IMAGE_FILE_PATH}avakian_meme.jpg'))

client.run(DISCORD_API_KEY)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

