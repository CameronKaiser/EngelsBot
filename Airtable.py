# Third Party
from   pyairtable import Api

# Local Modules
from   Configuration import (AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_MEMBERS_TABLE_ID, AIRTABLE_TICKETS_TABLE_ID)

api = Api(AIRTABLE_API_KEY)

def update_members_table(members):
    table = api.table(AIRTABLE_BASE_ID, AIRTABLE_MEMBERS_TABLE_ID)

    records = table.all()

    existing_members = {}
    for record in records:
        existing_members[record['fields']['Username']] = record

    records_to_create = []
    records_to_patch  = []
    for member_username in members:
        member = members[member_username]

        record_fields = {
                          'Username'            : member.username,
                          'Nickname'            : member.nickname,
                          'Committees (Link)'   : member.committees,
                          'Organizations (Link)': member.organizations,
                          'Roles (Link)'        : member.roles,
                          'Avatar'              : member.avatar
                          }

        if member.relative_activity_level is not None:
            record_fields['Relative Activity'] = member.relative_activity_level
            record_fields['Activity'         ] = member.activity_level
            record_fields['Monthly Messages' ] = member.message_count

        if member_username in existing_members:

            record_id = existing_members[member_username]['id']
            record    = { 'id': record_id, 'fields': record_fields }

            records_to_patch.append(record)

        else:
            record = record_fields

            records_to_create.append(record)

    table.batch_create(records_to_create, typecast=True)
    table.batch_update(records_to_patch , typecast=True)

    return True

def upload_ticket(file_name, ticket_name, closer):
    table    = api.table(AIRTABLE_BASE_ID, AIRTABLE_TICKETS_TABLE_ID)
    response = table.create({ 'Name': ticket_name, 'Closer': closer }, typecast=True)

    with open(file_name, "rb") as f:
        file_bytes = f.read()

    table.upload_attachment(response['id'], 'File', file_name, content=file_bytes, content_type='text/plain')