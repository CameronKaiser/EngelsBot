# Local Modules
from typing import Any, Dict, Optional
from dataclasses import dataclass

# Easy Access
from Configuration import ROLES

@dataclass
class Endpoint:
    url    : str
    method : str

@dataclass
class Response:
    status  : int
    url     : str
    headers : Dict[str, str]
    json    : Optional[Dict[str, Any]]

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

class SolidarityUser:

    def __init__(self, user):
        self.data = user

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