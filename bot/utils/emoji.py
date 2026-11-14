# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import re

"""
Centralized emoji module for the UND bot.
All emoji definitions are stored here for easy management and consistency.
"""

# ============================================================================
# DISCORD CUSTOM EMOJIS (Static)
# ============================================================================
BOOST = "<:boost:1571192790493167738>"
BUG_HUNTER = "<:BugHunterLevel1:1571192607550210101>"
BUG_HUNTER_LVL2 = "🐛"
CAST = "<:zcast:1571192778849919036>"
CERTIFIED_MODERATOR = "<:CertifiedDiscordModerator:1571192802262650911>"
CHANNEL = "<:channel:1571192695316283442>"
CODEBASE = "<:codebase:1571192652605427713>"
CODED = "<:coded:1571192850077589706>"
CROSS = "<:zcross:1571192938698907779>"
CROSS_ALT = "<:CrossIcon:1571192665339338888>"
CUTE_CUTE_CUTE = "<:Cute_Cute_Cute:1571192724239941694>"
DELETE = "<:delete:1571192625413881866>"
DELETE_ALT1 = "<:delete:1571192625413881866>"
DENIED = "<:Denied:1571193053358596198>"
DISABLE = "<:Disable:1571192678392008734>"
DND = "<:dnd:1571192672226508871>"
EARLY_SUPPORTER = "<:EarlySupporter:1571192767785205860>"
ENABLE = "<:Enable:1571192656078315591>"
ERROR = "❌"
FORWARD = "<:forward:1571192972392009880>"
GAMES = "<:games:1571192893786423411>"
HANDSHAKE = "<:handshake:1571192904947601670>"
HAPPY_PANDA = "<:happy_panda:1571192798810476626>"
HEADMOD = "<:headmod:1571193008181743747>"
HEART3 = "<:heart3:1571192997897437317>"
HEART_EM = "<:heart_em:1571193057330601991>"
HEERIYE = "<:Heeriye:1571192642057011230>"
HOME = "<:icons_home:1571192935591059587>"
HYPESQUAD_BRILLIANCE = "<:Hypesquad_Brilliance:1571192794981343294>"
ICONLOAD = "<:iconLoad:1571192782075334832>"
ICONS_CHANNEL = "<:icons_channel:1571192897057857546>"
ICONS_MUSIC = "<:icons_music:1571192628714934374>"
ICONS_PAUSE = "<:icons_pause:1571192649208299602>"
ICONS_PLUS = "<:icons_plus:1571193012405407844>"
ICONS_WARNING = "<:icons_warning:1571192688378773718>"
ICONS_WARNING_ALT1 = "<:icons_warning:1571192688378773718>"
ICON_BROWSER = "<:icon_browser:1571192838186864770>"
IDLE = "<:idle:1571192826849398894>"
INDEX = "<:index:1571193081938841610>"
INFO = "<:info:1571192634486030497>"
KING = "<:king:1571192771530858516>"
LEVEL_UP = "<:zlevelup:1571193078532935731>"
LOCK = "<:lock:1571192761170788475>"
MANAGER = "<:manager:1571192764496879717>"
MENTION = "<:zyrox_mention:1571192877860528208>"
MESSAGE = "<:zmsg:1571192978461036565>"
MINECRAFT = "<:zmc:1571192929064714250>"
ML_CROSS = "<:ml_cross:1571192981497847808>"
MUSIC = "<:zmusic:1571192811267555438>"
MUSICSTOP_ICONS = "<:musicstop_icons:1571192610712846394>"
MUTE = "<:zmute:1571193040075493519>"
NEW = "<:New:1571192698633986279>"
NEXT = "<:icons_next:1571192718044954765>"
NEXT_ALT1 = "<:next:1571192958466920568>"
OFFLINE = "<:offline:1571192604299894817>"
PARTNER_BADGE = "🤝"
PC = "<:pc:1571193049453822093>"
PIN = "<:zpin:1571193071201165322>"
PREVIOUS = "<:next:1571192958466920568>"
RED_BUTTON = "<:red_button:1571192692040532008>"
RED_PIN = "<:red_pin:1571192754766094486>"
REWIND = "<:rewind1:1571192884282130433>"
REWIND_ALT1 = "<:rewind:1571192984630726656>"
SEED = "<:zseed:1571192890615668817>"
SHUFFLE = "<:shuffle:1571192681487401051>"
SKIP = "<:skip:1571192887402700870>"
STAR = "<:starr:1571192853500010706>"
SWORD = "<:zsowrd:1571192701737762866>"
SYSTEM = "<:zyrox_system:1571193085415784538>"
THUNDER = "<:zyroxthunder:1571193036380184690>"
TICK = "<:ztick:1571192911532392561>"
TICKET = "<:zticket:1571192751268302948>"
TICK_ALT = "<:tick:1571192818528034939>"
TIME = "<:zyrox_time:1571192774869516371>"
TIMER = "<:ztimer:1571193061567103126>"
UNLOCK = "<:unlock:1571192807178113086>"
UPTIME = "<:uptime:1571192601288249344>"
U_ADMIN = "<:U_admin:1571193088548937838>"
WARNING = "<:warning:1571192881098789074>"
WARNING_ALT = "<:warning:1571192881098789074>"
WIFI = "<:zwifi:1571192740753186999>"
ZAI = "<:zai:1571192730674266212>"
ZARROW = "<:zArrow:1571192714450436098>"
ZBACK = "<:zback:1571192621873766593>"
ZBAN = "<:zban:1571192856817958974>"
ZBOT = "<:zbot:1571192747849818236>"
ZCIRCLE = "<:zcircle:1571192925642035351>"
ZCIRCLE_ALT1 = "<:zcircle:1571192925642035351>"
ZCLOUD = "<:zCloud:1571193001747808258>"
ZCOUNTING = "<:zcounting:1571192975449657435>"
ZCROSS = "<:zcross:1571192938698907779>"
ZDIL = "<:zdil:1571192863973445764>"
ZHUMAN = "<:zHuman:1571193032378679357>"
ZMODULE = "<:zmodule:1571192871158288384>"
ZMUSICPAUSE = "<:zmusicpause:1571192707962110014>"
ZPAUSE = "<:zpause:1571192867823685823>"
ZPEOPLE = "<:zpeople:1571193019900891309>"
ZPLAY = "<:zplay:1571192987424137247>"
ZPLUS = "<:zplus:1571192786110255127>"
ZROCKET = "<:zrocket:1571192721194881215>"
ZSAFE = "<:zSafe:1571192845417848882>"
ZSETTINGS = "<:zsettings:1571192659291148420>"
ZTADA = "<:ztada:1571193028461207733>"
ZTICK = "<:Ztick:1571192990800806074>"
ZUNMUTE = "<:zunmute:1571192965643239634>"
ZWARNING = "<:zwarning:1571192922337185952>"
ZWRENCH = "<:zwrench:1571192874723184791>"
ZYROXCONNECTION = "<:zyroxconnection:1571193016058650635>"
ZYROXHAMMER = "<:zyroxhammer:1571192946336997517>"
ZYROXLINKS = "<:zyroxlinks:1571192744582324244>"
ZYROXSYS = "<:zyroxsys:1571193074883764224>"
ZYROX_CODE = "<:zyrox_code:1571192704975634492>"
ZYROX_COMMAND = "<:zyrox_command:1571192915127046264>"
ZYROX_GLOBAL = "<:zyrox_global:1571192834378178741>"
ZYROX_OWNER = "<:zyrox_owner:1571192961905987755>"
ZYROX_SEARCH = "<:zyrox_search:1571193004910190734>"

# ============================================================================
# DISCORD CUSTOM EMOJIS (Animated)
# ============================================================================
ACTIVE_DEVELOPER = "<a:Active_Developer:1571192949553889320>"
ARROWRED = "<a:ArrowRed:1571192727431946250>"
BLACKCROWN = "<a:BlackCrown:1571192617813811301>"
BLOBPART = "<a:blobpart:1571192638567092304>"
BOOSTS = "<a:boosts:1571192830515478670>"
EARLY_VERIFIED_BOT_DEV = "<a:EarlyVerifiedBotDeveloper:1571192645466722396>"
EMOTE = "<a:emote:1571192994378420375>"
GIFD = "<a:GIFD:1571192842150355024>"
GIFN = "<a:GIFN:1571193045662302401>"
HYPESQUAD_BALANCE = "<a:a_Hypesquad_Balance:1571192918369247322>"
HYPESQUAD_BRAVERY = "<a:a_Hypesquad_Bravery:1571192900761551081>"
HYPESQUAD_EVENTS = "🏆"
KING_ALT1 = "<a:king:1571192771530858516>"
LOADING = "<a:loading:1571192662571225098>"
LOADINGRED = "<a:loadingred:1571193064188551243>"
LOADING_ALT1 = "<a:loading:1571192662571225098>"
MAX__A = "<a:max__A:1571192668942241813>"
MENTION_ALT1 = "<a:mention:1571192814568612044>"
MINGLE = "<a:mingle:1571193067845714102>"
MOBILE = "<a:mobile:1571192675196084374>"
MUSIC_ALT1 = "<a:music:1571192684805099622>"
NITRO_BOOST = "<a:nitroboost:1571192908705697913>"
ONLINE = "<a:online:1571192822961545246>"
PREMIUM = "<a:premium:1571192757958221865>"
RACECAR64 = "<a:racecar64:1571192734054752286>"
REDDOT = "<a:reddot:1571192968919126121>"
REDHEART = "<a:RedHeart:1571192737753993438>"
REDRULESBOOK = "<a:RedRulesBook:1571192631474528381>"
SG_RD = "<a:sg_rd:1571192711413768202>"
STAFF = "<a:staff:1571193024006848695>"
STAR_ALT1 = "<a:Star:1571192860236324866>"
STAR_ALT2 = "<a:star:1571192952892428408>"
TADAA = "<a:TADAA:1571192614735323166>"
TIMER_ALT1 = "<a:timer:1571192942675370185>"
_37496ALERT = "<a:37496alert:1571192931975561359>"

# ============================================================================
# DISCORD BADGE EMOJIS MAPPING (Dictionary)
# ============================================================================
DISCORD_BADGE_EMOJIS = {
    "staff": STAFF,
    "partner": PARTNER_BADGE,
    "hypesquad": HYPESQUAD_BRILLIANCE,
    "hypesquad_bravery": HYPESQUAD_BRAVERY,
    "hypesquad_brilliance": HYPESQUAD_BRILLIANCE,
    "hypesquad_balance": HYPESQUAD_BALANCE,
    "bug_hunter": BUG_HUNTER,
    "bug_hunter_level_2": BUG_HUNTER_LVL2,
    "early_supporter": EARLY_SUPPORTER,
    "early_verified_bot_developer": EARLY_VERIFIED_BOT_DEV,
    "certified_moderator": CERTIFIED_MODERATOR,
    "active_developer": ACTIVE_DEVELOPER,
    "discord_mod": CERTIFIED_MODERATOR,
}

# ============================================================================
# UNICODE EMOJIS
# ============================================================================
ARROW_DOWN = "⬇️"
ARROW_LEFT = "⬅️"
ARROW_RIGHT = "➡️"
ARROW_UP = "⬆️"
BLOCK = "🚫"
BUBBLE_TEA = "🧋"
CELEBRATE = "🎉"
CHERRIES = "🍒"
CLOCK = "⏱️"
COOKIE = "🍪"
CURSOR = "🖱️"
DIZZY = "🥴"
ERROR_UNICODE = "❌"
GAME_CONTROLLER = "🎮"
HEARTS = "💕"
JAVA_COFFEE = "☕"
LAUGH1 = "😂"
LAUGH2 = "🤣"
LAUGH3 = "😆"
LOCK_UNICODE = "🔒"
MONEY = "💸"
MOON = "🌙"
NOTE = "📝"
PAPER = "\U0001f4f0"
PEACH = "🍑"
REFRESH = "🔄"
ROCK = "\U0001faa8"
SCISSORS = "\U00002702"
SHOCKED = "😳"
SPARKLE = "✨"
STAR_UNICODE = "⭐"
STOP_BUTTON = "⏹️"
SUCCESS = "✅"
TARGET = "🎯"
TONGUE_OUT = "😜"
UPSIDE_DOWN = "🙃"
WARNING_UNICODE = "❗"

# ============================================================================
# EMOJI COLLECTIONS BY CATEGORY (Dictionaries)
# ============================================================================
GAME_BUTTONS = {
    "up": ARROW_UP,
    "down": ARROW_DOWN,
    "left": ARROW_LEFT,
    "right": ARROW_RIGHT,
    "stop": STOP_BUTTON,
    "target": "🎯",
}

ACTION_EMOJIS = {
    "success": SUCCESS,
    "error": ERROR_UNICODE,
    "warning": WARNING_UNICODE,
    "clock": CLOCK,
    "refresh": REFRESH,
}

RPS_CHOICES = {
    "rock": ROCK,
    "scissors": SCISSORS,
    "paper": PAPER,
}

BUTTON_EMOJIS = {
    "note": NOTE,
    "privacy": LOCK_UNICODE,
    "claim": STAR_UNICODE,
    "untrust": ERROR_UNICODE,
    "block": BLOCK,
    "target": "🎯",
    "edit": "✏️",
}

REACTION_TEST_EMOJIS = [
    COOKIE, CELEBRATE, BUBBLE_TEA, CHERRIES, PEACH, MONEY, MOON, HEARTS
]

FUN_EMOJIS = [
    LAUGH1, LAUGH2, LAUGH3, SHOCKED, DIZZY, UPSIDE_DOWN, TONGUE_OUT
]

MINECRAFT_EMOJIS = {
    "success": SUCCESS,
    "error": ERROR_UNICODE,
    "warning": WARNING_UNICODE,
    "clock": CLOCK,
    "refresh": REFRESH,
    "java": JAVA_COFFEE,
}

# ============================================================================
# FEATURE EMOJIS (Dictionaries)
# ============================================================================
MODERATION_EMOJIS = {
    "warn": WARNING,
    "mute": MUTE,
    "ban": SWORD,
    "kick": SWORD,
    "lock": LOCK,
}

TICKET_EMOJIS = {
    "ticket": TICKET,
    "close": ERROR,
    "open": SUCCESS,
    "pin": PIN,
}

LEVEL_EMOJIS = {
    "level_up": LEVEL_UP,
    "sparkle": SPARKLE,
    "achievement": STAR,
}

UTILITY_EMOJIS = {
    "music": MUSIC,
    "system": SYSTEM,
    "new": NEW,
    "message": MESSAGE,
    "wifi": WIFI,
    "cast": CAST,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_badge_emoji(badge_name: str) -> str:
    """
    Get Discord badge emoji by name.
    
    Args:
        badge_name: The name of the badge (e.g., 'staff', 'partner', 'bug_hunter')
    
    Returns:
        The emoji string for the badge, or None if not found
    """
    return DISCORD_BADGE_EMOJIS.get(badge_name.lower())


def get_action_emoji(action: str) -> str:
    """
    Get emoji for a common action.
    
    Args:
        action: The action name (e.g., 'success', 'error', 'warning')
    
    Returns:
        The emoji string for the action
    """
    return ACTION_EMOJIS.get(action.lower())


def get_button_emoji(button_type: str) -> str:
    """
    Get emoji for a button type.
    
    Args:
        button_type: The button type (e.g., 'note', 'privacy', 'claim')
    
    Returns:
        The emoji string for the button
    """
    return BUTTON_EMOJIS.get(button_type.lower())



_CUSTOM_EMOJI = re.compile(r"^<a?:[A-Za-z0-9_]+:\d+>$")


def safe_emoji(value, fallback="🔹"):
    """Return an emoji string that Discord accepts in components.

    Application emojis (custom, synced by utils/sync_emojis.py) are allowed;
    stray whitespace or malformed references fall back to a unicode emoji.
    """
    text = str(value or "").strip()
    if not text or len(text) > 80:
        return fallback
    if _CUSTOM_EMOJI.match(text):
        return text
    if all(ord(ch) > 0x2000 for ch in text):
        return text
    return fallback


# ============================================================================
# COMPATIBILITY ALIASES
# ============================================================================

# Common aliases for frequently used emojis
CHECKMARK = TICK
CROSS_MARK = CROSS
CHECK = SUCCESS
FAIL = ERROR
OK = SUCCESS
NOT_OK = ERROR



# ── plain unicode → application emoji ────────────────────────────────────────
UNICODE_ALIASES = {
    '✅': '<:ztick:1571192911532392561>',
    '✔️': '<:Ztick:1571192990800806074>',
    '❌': '<:zcross:1571192938698907779>',
    '✖️': '<:zcross:1571192938698907779>',
    '🔒': '<:lock:1571192761170788475>',
    '🔓': '<:unlock:1571192807178113086>',
    '⏳': '<:ztimer:1571193061567103126>',
    '💬': '<:zmsg:1571192978461036565>',
    '✉️': '<:zmsg:1571192978461036565>',
    '👢': '<:zban:1571192856817958974>',
    '🌍': '<:zyrox_global:1571192834378178741>',
    '⭐': '<:starr:1571192853500010706>',
    '🔄': '<:shuffle:1571192681487401051>',
    '🗑️': '<:delete:1571192625413881866>',
    '🚫': '<:Denied:1571193053358596198>',
    '➕': '<:icons_plus:1571193012405407844>',
    '🔴': '<:red_button:1571192692040532008>',
    '🟢': '<:Enable:1571192656078315591>',
    '📊': '<:zyroxsys:1571193074883764224>',
    '📨': '<:zmsg:1571192978461036565>',
    '🔗': '<:zyroxlinks:1571192744582324244>',
    '🛡️': '<:zSafe:1571192845417848882>',
    '👑': '<:king:1571192771530858516>',
    '🎫': '<:zticket:1571192751268302948>',
    '⚠️': '<:warning:1571192881098789074>',
    '🕒': '<:zyrox_time:1571192774869516371>',
    '🔍': '<:zyrox_search:1571193004910190734>',
    '🏠': '<:icons_home:1571192935591059587>',
    '🎮': '<:games:1571192893786423411>',
    '🔔': '<:zyrox_mention:1571192877860528208>',
    '⚙️': '<:zsettings:1571192659291148420>',
    '🧩': '<:zmodule:1571192871158288384>',
    '🎵': '<:zmusic:1571192811267555438>',
    '📢': '<:zyrox_mention:1571192877860528208>',
    '💞': '<:heart3:1571192997897437317>',
    '❤️': '<:heart_em:1571193057330601991>',
    '💻': '<:pc:1571193049453822093>',
    '⬅️': '<:next:1571192958466920568>',
    '➡️': '<:icons_next:1571192718044954765>',
}


def custom(text: str) -> str:
    """Swap normal unicode emojis for the bot's own application emojis."""
    if not text:
        return text
    for unicode_emoji, ref in UNICODE_ALIASES.items():
        text = text.replace(unicode_emoji, ref)
    return text


def ui_emoji(value):
    """Return the application emoji for a unicode emoji (or the value itself)."""
    return UNICODE_ALIASES.get(value, value)
