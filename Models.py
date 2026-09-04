# Local Modules
from datetime import datetime
from typing          import Any
from dataclasses     import dataclass
from dateutil.parser import isoparse

import Mutables
# Easy Access
from Configuration import ROLES
from Mutables      import banned_scope_ids

@dataclass
class Endpoint:
    url    : str
    method : str

@dataclass
class Response:
    status  : int
    url     : str
    headers : dict[str, str]
    json    : dict[str, Any] | None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

class GovernmentMeeting:

    def __init__(self, date, time, location, title, agenda_url, flock_detected):
        self.date       = date
        self.time       = time
        self.location   = location
        self.title      = title
        self.agenda_url = agenda_url
        self.flock_detected = flock_detected

    def __str__(self):
        message = f"- **{self.title}**\n"         \
                  f"  - {self.date} - {self.time}\n" \
                  f"  - {self.location}"

        if self.flock_detected:
            message += "\n  - 🚨 FLOCK ACTIVITY DETECTED"

        if self.agenda_url:
            message += f"\n  - ([see agenda]({self.agenda_url}))"

        return message

class SolidarityUser:

    def __init__(self, user):
        self.data = user

class SolidarityEvent:

    def __init__(self, event, session):

        self.id           = str(session.get('id'))
        self.data         = event
        self.start_time   = datetime.fromisoformat(session['start_time'].replace("Z", "+00:00"))
        self.end_time     = datetime.fromisoformat(session[  'end_time'].replace("Z", "+00:00"))
        self.tags         = [tag.replace('_', '').replace('-', '').lower() for tag in event.get('tags') + event.get('campaign_tags') + session.get('tags')]
        self.scope_id     = event.get('scope_id')
        self.private      = 'private' in self.tags
        self.virtual_pair = bool(session.get('paired_meci_id') and str(session.get('event_type')) == 'virtual')
        self.hide_address = event.get('hide_address_until_rsvp')

        description = SolidarityEvent.build_description(event, session)
        summary     = SolidarityEvent.build_summary    (self, event, session)

        self.vague_title = summary
        self.dated_title = f"{summary} - {datetime.fromisoformat(session['start_time'].replace('Z', '+00:00')).strftime('%m/%d/%y')}"

        payload   = ({'id' : str(session.get('id'             )),
                 'summary' :                  summary           ,
                'location' :     session.get('location_address') if not self.hide_address else 'Address revealed upon RSVP',
             'description' :                  description       ,
                   'start' : {'dateTime': session['start_time'].replace("Z", "+00:00")},
                     'end' : {'dateTime': session['end_time'  ].replace("Z", "+00:00")},
                  'status' : 'confirmed' if not (self.private or self.virtual_pair or self.scope_id in banned_scope_ids) else 'cancelled'})

        self.payload      = SolidarityEvent.normalize(payload)


    def __eq__(self, other):
        if isinstance(other, GoogleEvent):
            p1 = self .payload
            p2 = other.payload

            event_id = p1.get('id')

            if p1.get(    'status') != p2.get('status'    ):
                print(f"Event {event_id} differential: status {p1.get('status')} != {p2.get('status')}")
                return False
            if p1.get(    'summary') != p2.get('summary'    ):
                print(f"Event {event_id} differential: summary {p1.get('summary')} != {p2.get('summary')}")
                return False
            if p1.get(   'location') != p2.get('location'   ):
                print(f"Event {event_id} differential: location {p1.get('location')} != {p2.get('location')}")
                return False
            if p1.get('description') != p2.get('description'):
                print(f"Event {event_id} differential: description {p1.get('description')} != {p2.get('description')}")
                return False
            if isoparse(p1.get('start').get('dateTime')) != isoparse(p2.get('start').get('dateTime')):
                print(f"Event {event_id} differential: start {isoparse(p1.get('start').get('dateTime'))} != {isoparse(p2.get('start').get('dateTime'))}")
                return False
            if isoparse(p1.get('end').get('dateTime')) != isoparse(p2.get('end').get('dateTime')):
                print(f"Event {event_id} differential: end {isoparse(p1.get('end').get('dateTime'))} != {isoparse(p2.get('end').get('dateTime'))}")
                return False

            return True
        return NotImplemented

#   If Soltech has an empty string, convert to None for Google
    @staticmethod
    def normalize(payload):
        for key in payload:
            if payload [key] == '':
                payload[key] =  None

        return payload

    @staticmethod
    def build_description(event, session):
        description = None
        if event.get('description'):
            description = event.get('description')

        if session.get('note'):
            if description:
                description += f"\n\n{session.get('note')}"
            else:
                description = session.get('note')

        if event.get('event_page_url'):
            if description:
                description += f"\n\nRSVP: {event.get('event_page_url')}"
            else:
                description = f"RSVP: {event.get('event_page_url')}"

        return description

#   This method adds X number of invisible spaces to the title, where X corresponds with the tag ordering set in Configuration.
#   If you embed your google calendar on your website, you can then use javascript to check how many invisible spaces (alt + 0173)
#   are present in the title and then color code the object based on that

    def build_summary(self, event, session):

        summary = f"{event.get('title')} - {session.get('title')}" if session.get('title') != event.get('title') else event.get('title')

        i = 1
        for tag in Mutables.calendar_tags:
            if tag in self.tags:
                summary += ('­' * i)
                break

            i += 1

        return summary

class GoogleEvent:

    def __init__(self, event, calendar_id):
        self.id          = event.get('id')
        self.data        = event
        self.calendar_id = calendar_id
        self.status      = event.get('status')
        self.payload     = {         'id' : event.get('id'         ),
                                'summary' : event.get('summary'    ),
                               'location' : event.get('location'   ),
                            'description' : event.get('description'),
                                  'start' : event.get('start'      ),
                                    'end' : event.get('end'        ),
                                 'status' : event.get('status'     )}

@dataclass
class Quote:

    text        : str
    number      : int
    user_id     : int
    jump_url    : str
    airtable_id : str
    message_id  : int

class QuoteRequest:

    valid  = None
    number = None
    delete = None

    def __init__(self, request_string):
        parameters = request_string.split()

        if parameters[0] == '.quote':
            self.valid = True

        for parameter in parameters:
            parameter = parameter.replace('#', '')

            if parameter == 'delete':
                self.delete = True

            if parameter.isdigit():
                self.number = int(parameter)

class Member:

    def __init__(self, member):

        committees    = []
        organizations = []
        other_roles   = []

        roles = member.roles

        for role in roles:
            if   role in ROLES.COMMITTEES:
                committees   .append(role.name)
            elif role in ROLES.ORGANIZATIONS:
                organizations.append(role.name)
            elif role.name != '@everyone':
                other_roles  .append(role.name)

        committees.sort()
        organizations.sort()
        other_roles.sort()

        self.username                = member.name
        self.nickname                = member.display_name
        self.committees              = committees
        self.organizations           = organizations
        self.roles                   = other_roles
        self.avatar                  = member.display_avatar.url
        self.message_count           = 0
        self.relative_activity_level = None
        self.activity_level          = None

    def to_csv_line(self):
        committee_string    = ', '.join(self.committees)
        organization_string = ', '.join(self.organizations)
        other_roles_string  = ', '.join(self.roles)

        return '"' + self.nickname + '",' + self.username + ',"' + committee_string + '","' + organization_string + '","' + other_roles_string + '"\n'