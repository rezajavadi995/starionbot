MESSAGES = {
    "en": {
        "choose_language": "Choose your language:",
        "join_required": "Please join the channel first, then tap verify membership.",
        "join_verified": "Membership verified. You can now continue.",
        "join_failed": "You are not a channel member yet.",
    },
    "fa": {
        "choose_language": "لطفا زبان خود را انتخاب کنید:",
        "join_required": "ابتدا در کانال عضو شوید و سپس تایید عضویت را بزنید.",
        "join_verified": "عضویت تایید شد. حالا می توانید ادامه دهید.",
        "join_failed": "هنوز عضو کانال نیستید.",
    },
}


def t(lang: str, key: str) -> str:
    if lang not in MESSAGES:
        lang = "en"
    return MESSAGES[lang][key]
