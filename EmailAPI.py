# Standard Library
import smtplib
from   email.message import EmailMessage

# Local Module
from Configuration import (SMTP_USER, SMTP_PORT, SMTP_HOST, SMTP_PASS)

#   Currently we don't use this programmatically. Originally we wanted to allow users to open tickets in email via Discord, but
#   you need to have a way of verifying that the destination email is theirs - you can't let them free-input, otherwise this
#   can be exploited. Only use if you have a way of ensuring the email can only go to places you've whitelisted.
def send_email(to_address, subject, body, cc=None, from_name=None):
    msg            = EmailMessage()
    msg["From"]    = SMTP_USER if from_name is None else f'{from_name} <{SMTP_USER}>'
    msg["To"]      = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    if cc:
        msg["Cc"] = cc

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
         smtp.login(SMTP_USER, SMTP_PASS)
         smtp.send_message(msg)
