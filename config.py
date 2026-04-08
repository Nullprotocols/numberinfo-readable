# config.py
# Owner and Admins
OWNER_ID = 8104850843
ADMIN_IDS = [5987905091]

# Force Join Channels
CHANNELS = [-1003090922367, -1003698567122, -1003672015073]
CHANNEL_LINKS = [
    "https://t.me/all_data_here",
    "https://t.me/osint_lookup",
    "https://t.me/legend_chats_osint"
]

# Log Channel – sirf Number Lookup ke liye
LOG_CHANNELS = {
    'num': -1003482423742,   # Apna actual log channel ID yahan dalen
}

# API Configuration – Only Number Lookup
APIS = {
    'num': {
        'url': 'https://ayaanmods.site/number.php?key=annonymous&number={}',
        'param': 'number',
        'log': LOG_CHANNELS['num'],
        'desc': 'Mobile number lookup',
        'extra_blacklist': ['API_Developer', 'channel_name', 'channel_link']
    },
}

DEV_USERNAME = "@Nullprotocol_X"
POWERED_BY = "NULL PROTOCOL"
BACKUP_CHANNEL = -1003740236326   # Apna backup channel ID yahan dalen
