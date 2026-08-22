import discord
from Configuration import CHANNELS, MEMBERS, ROLES, MESSAGES, EMOJIS, BRANCHES, FORUMTAGS, STEERING_EMAIL
from Ticket import TicketModal


class DiscordButtonHub(discord.ui.View):
    def __init__(self):
        #   We have to initialize the button and add the emoji after in the constructor otherwise it seems to initialize asychronously which means it
        #   happens before the EMOJIS class is hydrated, meaning it tries to inject an int, which fails. Time travel I guess, I don't know
        super().__init__(timeout=None)
        button = self.remove
    #   button.emoji = EMOJIS.ROSA or '✔️'

    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if ROLES.DSA_MEMBER not in interaction.user.roles:
            await interaction.response.send_message("This interaction is for DSA Members only.", ephemeral=True)
            return False

        return True

    @discord.ui.button(emoji="🔄", row=0, label="Reset all channels to defaults \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.blurple, custom_id='reset_roles_button')
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.user.remove_roles(ROLES.SOCIALITE, ROLES.PUNDIT, ROLES.JOANNA_CAMPAIGNER, ROLES.ANTIFLOCKER)
        await interaction.user.add_roles(ROLES.DSA_DISCORDER)
        await interaction.response.send_message(f'All roles and channels have been reset to their defaults.', ephemeral=True)

    @discord.ui.button(emoji="🙋", row=1, label="Toggle social / chat channels \u200b \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.green, custom_id='toggle_social_role_button')
    async def toggle_social(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ROLES.SOCIALITE not in interaction.user.roles:
            await interaction.user.add_roles(ROLES.SOCIALITE)
            await interaction.response.send_message(f"Social role added - you'll see the added social channels on the left!", ephemeral=True)
        else:
            await interaction.user.remove_roles(ROLES.SOCIALITE)
            await interaction.response.send_message(f"Social role removed.", ephemeral=True)

    @discord.ui.button(emoji="🗞️", row=1, label="Toggle news / theory channels", style=discord.ButtonStyle.green, custom_id='toggle_theory_button')
    async def toggle_theory(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ROLES.PUNDIT not in interaction.user.roles:
            await interaction.user.add_roles(ROLES.PUNDIT)
            await interaction.response.send_message(f"Pundit role added - you'll see the added news/theory channels on the left!", ephemeral=True)
        else:
            await interaction.user.remove_roles(ROLES.PUNDIT)
            await interaction.response.send_message(f"Pundit role removed.", ephemeral=True)

    @discord.ui.button(emoji="📈", row=2, label="Toggle Joanna Campaign Focus \u200b", style=discord.ButtonStyle.red, custom_id='toggle_joanna_button')
    async def toggle_joanna(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ROLES.JOANNA_CAMPAIGNER not in interaction.user.roles:
            await interaction.user.remove_roles(ROLES.SOCIALITE, ROLES.PUNDIT, ROLES.DSA_DISCORDER)
            await interaction.user.add_roles(ROLES.JOANNA_CAMPAIGNER)
            await interaction.response.send_message(f"Joanna Campaign focused - all non-critical channels hidden", ephemeral=True)
        else:
            await interaction.user.add_roles(ROLES.DSA_DISCORDER)
            await interaction.user.remove_roles(ROLES.JOANNA_CAMPAIGNER)
            await interaction.response.send_message(f"General channel visibility restored", ephemeral=True)

    @discord.ui.button(emoji="📷", row=2, label="Toggle Anti-Flock Focus \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.red, custom_id='toggle_flock_button')
    async def toggle_flock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if ROLES.ANTIFLOCKER not in interaction.user.roles:
            await interaction.user.remove_roles(ROLES.SOCIALITE, ROLES.PUNDIT, ROLES.DSA_DISCORDER)
            await interaction.user.add_roles(ROLES.ANTIFLOCKER)
            await interaction.response.send_message(f"Flock initiative focused - all non-critical channels hidden", ephemeral=True)
        else:
            await interaction.user.add_roles(ROLES.DSA_DISCORDER)
            await interaction.user.remove_roles(ROLES.ANTIFLOCKER)
            await interaction.response.send_message(f"General channel visibility restored", ephemeral=True)

class ActionHub(discord.ui.View):
    def __init__(self):
        #   We have to initialize the button and add the emoji after in the constructor otherwise it seems to initialize asychronously which means it
        #   happens before the EMOJIS class is hydrated, meaning it tries to inject an int, which fails. Time travel I guess, I don't know
        super().__init__(timeout=None)
        button = self.remove
    #   button.emoji = EMOJIS.ROSA or '✔️'

    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if ROLES.DSA_MEMBER not in interaction.user.roles and interaction.data["custom_id"] not in ["locale_button", "open_ticket_button", "open_email_ticket_button"]:
            await interaction.response.send_message("This interaction is for DSA Members only.", ephemeral=True)
            return False

        return True

    @discord.ui.button(emoji="📤", row=0, label="Submit Request to Communications \u200b \u200b \u200b", style=discord.ButtonStyle.blurple, custom_id='comms_request_buttom')
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CommsRequestModal(interaction.user, interaction.client))

    @discord.ui.button(emoji="🌎", row=0, label="Set your Region Role \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.blurple, custom_id='locale_button')
    async def locale(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LocationSetModal(interaction.user, interaction.client))

    @discord.ui.button(emoji="🏷", row=1, label="Purchase Reimbursement Form \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.blurple, custom_id='reimbursement_button')
    async def reimbursement(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f'Please use the following link to submit a reimbursement request: https://form.jotform.com/261456838739069',ephemeral=True)

    @discord.ui.button(emoji="📊", row=1, label="Ask our Treasurer Anything \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b \u200b", style=discord.ButtonStyle.blurple, custom_id='treasurer_button')
    async def treasurer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f'Feel free to @ {MEMBERS.TREASURER.mention} in {CHANNELS.DSA_CHATTING.mention}, DM them, or email at: treasurer@socodsa.org',ephemeral=True)

    @discord.ui.button(emoji="💬", row=2, label=" Open Ticket with Steering Committee", style=discord.ButtonStyle.green, custom_id='open_ticket_button')
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(interaction.user))

    @discord.ui.button(emoji="✉️", row=2, label="Open ticket with Steering via Email", style=discord.ButtonStyle.gray, custom_id='open_email_ticket_button')
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        subject = f'TICKET: {interaction.user.name} ({interaction.user.display_name}): '

        import urllib.parse
        url = (
            f"mailto:{STEERING_EMAIL}"
            f"?subject={urllib.parse.quote(subject)}"
        )
        await interaction.response.send_message(f'Please use the following personalized link to email Steering Committee: [Email Steering]({url})', ephemeral=True)

class LocationSetModal(discord.ui.Modal, title="Locale Role Setter"):
    def __init__(self, user, client):
        super().__init__()
        self.user   = user
        self.client = client

    location = discord.ui.Label(
        text="Locale",
        description="Set your local region. This can be used to ping certain areas in case of emergency (e.g. fires)",
        component=discord.ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label="Cotati / Rohnert Park", value="rohnert" ),
                discord.RadioGroupOption(label="North County"         , value="north"   ),
                discord.RadioGroupOption(label="Petaluma / Penngrove" , value="petaluma"),
                discord.RadioGroupOption(label="Santa Rosa"           , value="santa"   ),
                discord.RadioGroupOption(label="Sonoma Valley"        , value="sonoma"  ),
                discord.RadioGroupOption(label="West County"          , value="west"    ),
                discord.RadioGroupOption(label="None (remove role)"   , value="remove"  )
            ]
        )
    )

    async def on_submit(self, interaction: discord.Interaction):

        role = None
        if self.location.component.value == "rohnert":
            role = ROLES.ROHNERT_PARK
        elif self.location.component.value == "north":
            role = ROLES.NORTH
        elif self.location.component.value == "petaluma":
            role = ROLES.PETALUMA
        elif self.location.component.value == "santa":
            role = ROLES.SANTA_ROSA
        elif self.location.component.value == "sonoma":
            role = ROLES.SONOMA
        elif self.location.component.value == "west":
            role = ROLES.WEST

        await interaction.user.remove_roles(ROLES.ROHNERT_PARK, ROLES.NORTH, ROLES.PETALUMA, ROLES.SANTA_ROSA, ROLES.SONOMA, ROLES.WEST)

        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Location role set!", ephemeral=True)
        else:
            await interaction.response.send_message("Locale role removed!", ephemeral=True)

class CommsRequestModal(discord.ui.Modal, title="Comms Request Form"):
    def __init__(self, user, client):
        super().__init__()
        self.user   = user
        self.client = client

    request_type = discord.ui.Label(
        text="Request Type",
        component=discord.ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label="Content Creation" , value="content" ),
                discord.RadioGroupOption(label="Social Media Post", value="post"    ),
                discord.RadioGroupOption(label="Calendar Update"  , value="calendar"),
                discord.RadioGroupOption(label="Website Update"   , value="website" )
            ]
        )
    )

    headline = discord.ui.TextInput(
        label="Title",
        placeholder="e.g. Cold Ones with Comrades 8/24",
        style=discord.TextStyle.short,
        required=True,
    )

    notes = discord.ui.TextInput(
        label="Notes",
        placeholder="e.g. 8/24 6:00 - 9:00pm at Shady Oak Brewery",
        style=discord.TextStyle.long,
        required=True,
    )

    files = discord.ui.Label(
        text="Attachment (optional)",
        component=discord.ui.FileUpload(required=False, max_values=10),
    )

    async def on_submit(self, interaction: discord.Interaction):

        try:

            user = interaction.user

            await interaction.response.defer(ephemeral=True, thinking=True)

            request_type = self.request_type.component.value
            title        = self.headline.value
            notes        = self.notes.value
            files        = [await file.to_file() for file in self.files.component.values]

            tag = None
            if request_type == "content":
                tag = FORUMTAGS.COMMS_CONTENT
            elif request_type == "post":
                tag = FORUMTAGS.COMMS_POST
            elif request_type == "calendar":
                tag = FORUMTAGS.COMMS_CALENDAR
            elif request_type == "website":
                tag = FORUMTAGS.COMMS_WEBSITE

            await CHANNELS.COMMS_REQUESTS.create_thread(
                name=title,
                content=f"Request submitted by: {user.mention}\n\n{notes}",
                files=files,
                applied_tags=[FORUMTAGS.COMMS_OUTSTANDING, tag]
            )

            await interaction.followup.send("Request received! We'll fulfill it as soon as we can 🪄", ephemeral=True)

        except Exception as error:
            await CHANNELS.BOT_TESTING.send(f'‼️ User {user.mention}s comms request failed: {error}')
            await interaction.response.send_message(
                content   = f"We're sorry, an error occurred and we were unable to submit your request. A log has been sent to the admin team and we will try to fix this ASAP! In the meantime, feel free to let us know your request in {CHANNELS.DSA_CHATTING.mention}!",
                ephemeral = True)