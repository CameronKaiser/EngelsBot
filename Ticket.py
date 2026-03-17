# Standard Library
import asyncio
import os

# Third Party
import discord

# Local Modules
import Airtable
import EmailAPI
from   Configuration import (CATEGORIES, ROLES, STEERING_EMAIL, FILES_FILE_PATH, CHANNELS)

class CreateTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💬 Open Ticket with Steering Committee", style=discord.ButtonStyle.green, custom_id='open_ticket_button')
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(interaction.user))

    @discord.ui.button(label="✉️ Open ticket with Steering via Email", style=discord.ButtonStyle.primary, custom_id='open_email_ticket_button')
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        subject = f'TICKET: {interaction.user.name} ({interaction.user.display_name}): '

        import urllib.parse
        url = (
            f"mailto:{STEERING_EMAIL}"
            f"?subject={urllib.parse.quote(subject)}"
        )
        await interaction.response.send_message(f'Please use the following personalized link to email Steering Committee: [Email Steering]({url})', ephemeral=True)

    # Disabled due to potential exploits
    # @discord.ui.button(label="✉️ Open ticket with Steering via Email", style=discord.ButtonStyle.primary)
    # async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    #    await interaction.response.send_modal(EmailModal(interaction.user))

class TicketModal(discord.ui.Modal, title="Open a Ticket"):
    def __init__(self, user):
        super().__init__()
        self.user = user

    description = discord.ui.TextInput(
        label      = "Provide an opening message for Steering:",
        style      = discord.TextStyle.paragraph,
        required   = True,
        max_length = 1999
    )

    async def on_submit(self, interaction: discord.Interaction):
        server   = interaction.guild

        overwrites = {
            server.default_role           : discord.PermissionOverwrite(view_channel=False),
            self.user                     : discord.PermissionOverwrite(view_channel=True, send_messages=True),
            server.me                     : discord.PermissionOverwrite(view_channel=True),
            ROLES.STEERING_COMMITTEE      : discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await CATEGORIES.TICKETS.create_text_channel(
            name       = f"ticket-{self.user.name}",
            overwrites = overwrites,
            reason     = "User Requested Ticket"
        )

        embed = discord.Embed(
            title       = f"{self.user.display_name}'s ({self.user.name}) Ticket",
            description = f"**Message provided:**\n{self.description.value}",
            color       = discord.Color.blue()
        )

        await channel.send(content = f'{ROLES.STEERING_COMMITTEE.mention}, {self.user.mention}', embed=embed, view=CloseTicketButton())

        await interaction.response.send_message(
            content   = f"Your ticket has been created at: {channel.mention}",
            ephemeral = True
        )
#   Currently not in use due to potential exploits
class EmailModal(discord.ui.Modal, title="Open a Ticket via Email"):
    def __init__(self, user):
        super().__init__()
        self.user = user

    user_email = discord.ui.TextInput(
        label       = "Please Enter your Email Address",
        placeholder = "comrade@socodsa.org",
        required    = True,
        style       = discord.TextStyle.short
    )

    email_subject = discord.ui.TextInput(
        label    = "Provide a Subject line for your email",
        required = True,
        style    = discord.TextStyle.short
    )

    email_body = discord.ui.TextInput(
        label    = "Provide a message for Steering",
        required = True,
        style    = discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_email    = self.user_email.value
        email_subject = self.email_subject.value
        email_body    = self.email_body.value

        try:

            EmailAPI.send_email(STEERING_EMAIL, f'TICKET: {self.user.name} ({self.user.display_name}): {email_subject}', email_body,
                                cc        = user_email,
                                from_name ='SoCo DSA Steering Committee')

            await interaction.response.send_message(
                "Your ticket has been successfully opened - it should be in your email and we'll try to respond soon!",
                ephemeral=True
            )

        except Exception as e:

            await interaction.response.send_message(
                "Unfortunately the email could not be sent, potentially due to service disruptions. We've been notified of the issue and will try to fix it "
                "soon, but consider opening a ticket in discord using the other button in the meantime!",
                ephemeral=True
            )

            await CHANNELS.BOT_TESTING.send(f'Ticket "{email_subject}" failed to be opened via email: ({e})')

class CloseTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id='close_ticket_button')
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("Thank you! Ticket will be closed shortly.", ephemeral=True)

        messages = []
        async for message in interaction.channel.history(limit=None):
            member = message.author.display_name
            urls   = []
            embeds = []
            for attachment in message.attachments:
                urls.append(attachment.url)

            for embed in message.embeds:
                embeds.append(f'{embed.title}\n{embed.description}')

            message_to_send = f'{member}: {message.content}'

            if embeds:
                message_to_send += '\n' + '\n'.join(embeds)

            if urls:
                message_to_send += '\n\n' + '\n'.join(urls)

            messages.append(message_to_send)

        file_name = f'{FILES_FILE_PATH}{interaction.channel.name}.txt'
        with open(file_name, "w", encoding="utf-8") as f:
            f.write("\n".join(reversed(messages)))

        closer = f'{interaction.user.name} ({interaction.user.display_name})'

        try:
            Airtable.upload_ticket(file_name, closer)
            os.remove(file_name)
        except Exception as e:
            bot_channel = interaction.guild.get_channel(1436468298635284520)
            await bot_channel.send(f'Ticket {interaction.channel.name} was closed but could not be uploaded to Airtable. Consequently, the log file has been preserved - upload it manually. ({e})')

        await asyncio.sleep(3)

        await CHANNELS.STEERING_COMMITTEE.send(f'> Ticket {interaction.channel.name} was closed by {closer}')
        await interaction.channel.delete(reason=f"Ticket closed by {closer}")
