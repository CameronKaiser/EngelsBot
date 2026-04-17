# Third Party
from random import randint

from   pyairtable import Api
from pyairtable.formulas import AND, GTE, Field, match

# Local Modules
from   Configuration import (AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_MEMBERS_TABLE_ID, AIRTABLE_TICKETS_TABLE_ID, AIRTABLE_VARIABLES_TABLE_ID, AIRTABLE_QUOTES_TABLE_ID)
from   Models        import Quote
import Mutables

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

async def get_quotes():

    try:
        quote_table = api.table(AIRTABLE_BASE_ID, AIRTABLE_QUOTES_TABLE_ID)

        quote_records = quote_table.all()

        for record in quote_records:
            text        =     record['fields']['Quote'     ]
            number      =     record['fields']['Number'    ]
            user_id     = int(record['fields']['User ID'   ])
            message_id  = int(record['fields']['Message ID'])
            jump_url    =     record['fields']['Jump URL'  ]
            airtable_id =     record['id'    ]
            Mutables.quote_cache[number] = Quote(text, number, user_id, jump_url, airtable_id, message_id)

        print(f'Successfully retrieved {len(quote_records)} quotes!')

    except Exception as error:
        print(f'Failed to retrieve quotes: {error}')

def upload_quote(quote, user_id, message_id, jump_url):
    try:
        quote_table  = api.table(AIRTABLE_BASE_ID, AIRTABLE_QUOTES_TABLE_ID)
        quote_record = quote_table.create({ 'Quote': quote, 'User ID': str(user_id) , 'Message ID': str(message_id), 'Jump URL': jump_url, 'Variable': 'Quote'}, typecast=True)

        return quote_record

    except Exception as error:
        return {'error': error}

def delete_quote(quote):
    try:
        quote_table  = api.table(AIRTABLE_BASE_ID, AIRTABLE_QUOTES_TABLE_ID)
        response     = quote_table.delete(quote.airtable_id)

        del Mutables.quote_cache[quote.number]

    except Exception as error:
        return {'error': error}
