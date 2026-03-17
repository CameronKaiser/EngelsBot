
~ EngelsBot ~

EngelsBot is an open-source Discord bot that performs functions useful to a DSA chapter (or any server, really) such as managing 
committee signups and user tickets, compositing data, converting categories to forums, sniping spammers, and simply 
being a rowdy comrade all around. During the 2025 Recruitment Drive he would provide tabulated rankings of
the chapters (and your chapter's place in it) on command. He does not use any AI, though some of his shenanigans
might make you think so!

EngelsBot was originally created by the Sonoma County chapter, but would love to find homes in new chapters! 

~ How To ~

There are a couple important things you'll want to know in order to set EngelsBot up in your own server
- API Keys and other sensitives must be configured in Configuration.py. If you don't have Airtable it's okay, you won't miss much. 
- You must set your Guild_ID and Chapter Name in Configuration.py
  - Take a look around Configuration.py and fill out everything that looks personalized to Sonoma County with your own information
- The Bot references channels, roles, members, etc. and you'll see IDs listed in configuration. You should set up at least the following to make sure engels works correctly:
  - BOT_TESTING - This should be a private channel. It is where Engels will send important logging information 
  - AUTO_MOD - This is where Engels sends sensitive data, for example logs of deleted messages
  - ADMIN_LIST - place all your admin roles in here - this will prevent non-admins from using sensitive commands
  - STEERING_COMMITTEE - Used to post ticket closure information
  - ENGELS_BOT - Used to make sure no one infinite loops the bot somehow
- You may run EngelsBot however you like, whether it be on a server or local device

~ What The Future Looks Like ~

I'd like to integrate engels with the Discord dashboard so that people less familiar with code can still use him.
This might prove limiting, so using Airtable as a configuration realm is also something I'm considering. For now
I'll continue to add updates and fun as needed.