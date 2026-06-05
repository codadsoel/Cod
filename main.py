# -*- coding: utf-8 -*-
# bot.py
# pip install -U "python-telegram-bot>=22.7"

import json
import logging
from datetime import datetime
from functools import lru_cache
import re
import unicodedata
from typing import Final, Optional, Tuple
from uuid import uuid4
from urllib.parse import quote
from urllib.request import urlopen

from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MessageEntity,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN: Final[str] = "8839469299:AAHIgmxP8EO7cgmn_DqrRZL1n5pi3bKDxhE"
ADMIN_GROUP_ID: Final[int] = -1004139636615
USDT_BEP20_ADDRESS: Final[str] = "0x17240860D43A34e376c9E1B2Ec11b50f4512F117"
AD_CHANNEL_ID: Final[int] = -1001342509205  # fallback channel id
AD_CHANNEL_USERNAME: Final[str] = "@COD_BUY_SELL"  # set "@your_channel_username" for a public channel

# Put your profile link here.
# Examples:
#   "tg://user?id=123456789"
#   "https://t.me/your_username"
SUPPORT_CONTACT_URL: Final[str] = "tg://user?id=7558330187"

# Main menu custom emoji ids
MENU_ICON_FAST_SALE = "5843553939672274145"
MENU_ICON_AUTO_AD = "5956148757899776734"
MENU_ICON_REQUEST_ACCOUNT = "6028226658543082010"
MENU_ICON_SUPPORT = "5890741826230423364"
MENU_ICON_ACCOUNT = "5906995262378741881"
MENU_ICON_LANGUAGE = "5778184941154078090"

# Page / text custom emoji ids
SUPPORT_HEADER_EMOJI_ID = "5875082500023258804"
LANGUAGE_HEADER_EMOJI_ID = "5778184941154078090"
ACCOUNT_HEADER_EMOJI_ID = "5883964170268840032"
ACCOUNT_BALANCE_EMOJI_ID = "5769403330761593044"
ACCOUNT_TIME_EMOJI_ID = "5778605968208170641"

# Support sticker file_id (NOT file_unique_id)
SUPPORT_STICKER_FILE_ID = "CAACAgIAAxkBAAFLgJlqIYEhAXQ6vAfs-9-p0VJM935twQACFyUAAtkoAAFL79-L7Fw-Jlc7BA"

DEFAULT_LANGUAGE = "English"
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

(
    MAIN_MENU,
    AD_VIDEO,
    AD_FORM,
    AD_CONFIRM,
    SALE_PLAN,
    SALE_PAYMENT_METHOD,
    SALE_CRYPTO_TXID,
    SALE_GIFT_CODE,
    REQUEST_ITEMS,
    REQUEST_BUDGET,
    REQUEST_CONFIRM,
    ACCOUNT_VIEW,
    LANGUAGE_VIEW,
) = range(13)

AD_CONFIRM_YES = "ad_confirm_yes"
AD_CONFIRM_NO = "ad_confirm_no"

PLAN_5 = "plan_5"
PLAN_10 = "plan_10"

PAY_CRYPTO = "pay_crypto"
PAY_GIFTCARD = "pay_giftcard"

REQ_CONFIRM_YES = "req_confirm_yes"
REQ_CONFIRM_NO = "req_confirm_no"

ACCOUNT_TOTAL_ORDERS = "account_total_orders"

LANG_ZH = "lang_zh"
LANG_HI = "lang_hi"
LANG_RU = "lang_ru"
LANG_FA = "lang_fa"
LANG_EN = "lang_en"
LANG_AR = "lang_ar"
LANG_HE = "lang_he"
LANG_UZ = "lang_uz"
LANG_IT = "lang_it"
LANG_TR = "lang_tr"
LANG_FR = "lang_fr"
LANG_ES = "lang_es"

BACK_MENU_TEXT = "ðŸ”™ Main Menu"
CANCEL_TEXT = "Cancel"

MENU_AUTO_AD = "Auto ad posting"
MENU_SUPPORT = "Support"
MENU_ACCOUNT = "Account"
MENU_FAST_SALE = "Fast sale"
MENU_REQUEST_ACCOUNT = "Request Account"
MENU_LANGUAGE = "Language"

PLACEHOLDER = "â—»"

AD_FORM_TEMPLATE = (
    "ðŸ”— | Synced on:\n\n"
    "ðŸ“¤| Description:\n\n"
    "Season:\n\n"
    "Legend:\n\n"
    "Multi:\n\n"
    "Mythic:\n\n"
    "Rank:\n\n"
    "Rare skin or gun:\n\n"
    "Price:\n\n"
    "Region"
)


def reset_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear temporary flow data, keep persistent user settings."""
    preserved = {
        key: value
        for key, value in context.user_data.items()
        if key in {"language", "language_code", "total_orders"}
    }
    context.user_data.clear()
    context.user_data.update(preserved)


def display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Unknown User"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "No username"
    return f"{full_name} ({username})"


def display_plain_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Unknown User"
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown User"


def user_id_str(update: Update) -> str:
    user = update.effective_user
    return str(user.id) if user else "N/A"


LANGUAGE_TO_GOOGLE = {
    "lang_zh": "zh-CN",
    "lang_hi": "hi",
    "lang_ru": "ru",
    "lang_fa": "fa",
    "lang_en": "en",
    "lang_ar": "ar",
    "lang_he": "he",
    "lang_uz": "uz",
    "lang_it": "it",
    "lang_tr": "tr",
    "lang_fr": "fr",
    "lang_es": "es",
}


def _current_google_lang(context: ContextTypes.DEFAULT_TYPE | None) -> str:
    if context is None:
        return "en"
    code = context.user_data.get("language_code", "lang_en")
    return LANGUAGE_TO_GOOGLE.get(code, "en")


@lru_cache(maxsize=4096)
def _google_translate_cached(text: str, target_lang: str) -> str:
    if not text or target_lang == "en":
        return text

    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=auto"
            f"&tl={quote(target_lang)}"
            f"&dt=t&q={quote(text)}"
        )
        with urlopen(url, timeout=8) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or text
    except Exception:
        return text


def tr(context: ContextTypes.DEFAULT_TYPE | None, text: str) -> str:
    return _google_translate_cached(text, _current_google_lang(context))


def _normalize_label(value: str) -> str:
    return re.sub(r"[\W_]+", "", (value or "").casefold())


def _store_ui_labels(context: ContextTypes.DEFAULT_TYPE | None, labels: dict[str, str]) -> dict[str, str]:
    if context is not None:
        context.user_data["_ui_labels"] = labels
    return labels


def _get_ui_labels(context: ContextTypes.DEFAULT_TYPE | None) -> dict[str, str]:
    if context is None:
        return {}
    labels = context.user_data.get("_ui_labels")
    return labels if isinstance(labels, dict) else {}


def ui_label(context: ContextTypes.DEFAULT_TYPE | None, canonical_text: str) -> str:
    """Return the currently active label for a canonical text and keep it cached."""
    labels = _get_ui_labels(context)
    current = tr(context, canonical_text)
    if context is not None:
        labels[canonical_text] = current
        context.user_data["_ui_labels"] = labels
    return labels.get(canonical_text, current) or canonical_text


def button_text_matches(context: ContextTypes.DEFAULT_TYPE | None, received_text: str, canonical_text: str) -> bool:
    """Match a received button label against canonical, translated, or currently cached UI text."""
    received = _normalize_label((received_text or "").strip())
    if not received:
        return False

    candidates = {
        canonical_text,
        tr(context, canonical_text),
        _get_ui_labels(context).get(canonical_text, ""),
    }
    for candidate in candidates:
        if candidate and _normalize_label(candidate) == received:
            return True
    return False


def menu_button(text: str, icon_custom_emoji_id: str) -> KeyboardButton:
    if icon_custom_emoji_id:
        return KeyboardButton(text=text, icon_custom_emoji_id=icon_custom_emoji_id)
    return KeyboardButton(text=text)


def main_menu_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> ReplyKeyboardMarkup:
    labels = _store_ui_labels(
        context,
        {
            MENU_FAST_SALE: tr(context, MENU_FAST_SALE),
            MENU_AUTO_AD: tr(context, MENU_AUTO_AD),
            MENU_REQUEST_ACCOUNT: tr(context, MENU_REQUEST_ACCOUNT),
            MENU_SUPPORT: tr(context, MENU_SUPPORT),
            MENU_ACCOUNT: tr(context, MENU_ACCOUNT),
            MENU_LANGUAGE: tr(context, MENU_LANGUAGE),
        },
    )
    return ReplyKeyboardMarkup(
        [
            [menu_button(labels[MENU_FAST_SALE], MENU_ICON_FAST_SALE)],
            [
                menu_button(labels[MENU_AUTO_AD], MENU_ICON_AUTO_AD),
                menu_button(labels[MENU_REQUEST_ACCOUNT], MENU_ICON_REQUEST_ACCOUNT),
            ],
            [
                menu_button(labels[MENU_SUPPORT], MENU_ICON_SUPPORT),
                menu_button(labels[MENU_ACCOUNT], MENU_ICON_ACCOUNT),
                menu_button(labels[MENU_LANGUAGE], MENU_ICON_LANGUAGE),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
    )


def nav_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> ReplyKeyboardMarkup:
    labels = _store_ui_labels(
        context,
        {
            BACK_MENU_TEXT: tr(context, BACK_MENU_TEXT),
            CANCEL_TEXT: tr(context, CANCEL_TEXT),
        },
    )
    return ReplyKeyboardMarkup(
        [
            [labels[BACK_MENU_TEXT]],
            [labels[CANCEL_TEXT]],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def ad_form_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    tr(context, "ðŸ“‹ Copy Form"),
                    copy_text=CopyTextButton(text=AD_FORM_TEMPLATE),
                )
            ]
        ]
    )


def ad_confirm_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "Confirm & Send"), callback_data=AD_CONFIRM_YES),
                InlineKeyboardButton(tr(context, "Cancel"), callback_data=AD_CONFIRM_NO),
            ]
        ]
    )


def sale_plan_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(context, "5 USD Package"), callback_data=PLAN_5)],
            [InlineKeyboardButton(tr(context, "10 USD Package"), callback_data=PLAN_10)],
        ]
    )


def payment_method_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(context, "USDT BEP20"), callback_data=PAY_CRYPTO)],
            [InlineKeyboardButton(tr(context, "Binance Gift Card"), callback_data=PAY_GIFTCARD)],
        ]
    )


def request_confirm_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "Send to Admin"), callback_data=REQ_CONFIRM_YES),
                InlineKeyboardButton(tr(context, "Cancel"), callback_data=REQ_CONFIRM_NO),
            ]
        ]
    )


def get_ad_channel_target() -> str | int:
    if AD_CHANNEL_USERNAME and AD_CHANNEL_USERNAME != "@your_channel_username":
        return AD_CHANNEL_USERNAME
    return AD_CHANNEL_ID


def build_main_menu_text(context: ContextTypes.DEFAULT_TYPE | None = None) -> str:
    return tr(context, "Choose one of the options below:")


async def send_main_menu_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        build_main_menu_text(context),
        reply_markup=main_menu_keyboard(context),
    )


AD_APPROVE_PREFIX = "ad_approve_"
AD_REJECT_PREFIX = "ad_reject_"
REQ_APPROVE_PREFIX = "req_approve_"
REQ_REJECT_PREFIX = "req_reject_"


def build_admin_ad_review_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("âœ… Approve", callback_data=f"{AD_APPROVE_PREFIX}{request_id}"),
                InlineKeyboardButton("âŒ Reject", callback_data=f"{AD_REJECT_PREFIX}{request_id}"),
            ]
        ]
    )


def build_admin_request_review_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("âœ… Approve", callback_data=f"{REQ_APPROVE_PREFIX}{request_id}"),
                InlineKeyboardButton("âŒ Reject", callback_data=f"{REQ_REJECT_PREFIX}{request_id}"),
            ]
        ]
    )


def support_inline_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "Support"), url=SUPPORT_CONTACT_URL),
            ]
        ]
    )


def account_inline_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "Support"), url=SUPPORT_CONTACT_URL),
                InlineKeyboardButton(tr(context, "Total Orders"), callback_data=ACCOUNT_TOTAL_ORDERS),
            ]
        ]
    )


def language_inline_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "Chinese ðŸ‡¨ðŸ‡³"), callback_data=LANG_ZH),
                InlineKeyboardButton(tr(context, "Hindi ðŸ‡®ðŸ‡³"), callback_data=LANG_HI),
            ],
            [
                InlineKeyboardButton(tr(context, "Russian ðŸ‡·ðŸ‡º"), callback_data=LANG_RU),
                InlineKeyboardButton(tr(context, "Farsi ðŸ‡®ðŸ‡·"), callback_data=LANG_FA),
            ],
            [
                InlineKeyboardButton(tr(context, "English ðŸ‡ºðŸ‡¸"), callback_data=LANG_EN),
                InlineKeyboardButton(tr(context, "Arabic ðŸ‡¸ðŸ‡¦"), callback_data=LANG_AR),
            ],
            [
                InlineKeyboardButton(tr(context, "Hebrew ðŸ‡®ðŸ‡±"), callback_data=LANG_HE),
                InlineKeyboardButton(tr(context, "Uzbekcha ðŸ‡ºðŸ‡¿"), callback_data=LANG_UZ),
            ],
            [
                InlineKeyboardButton(tr(context, "Italiano ðŸ‡®ðŸ‡¹"), callback_data=LANG_IT),
                InlineKeyboardButton(tr(context, "Turkce ðŸ‡¹ðŸ‡·"), callback_data=LANG_TR),
            ],
            [
                InlineKeyboardButton(tr(context, "French ðŸ‡«ðŸ‡·"), callback_data=LANG_FR),
                InlineKeyboardButton(tr(context, "Spanish ðŸ‡ªðŸ‡¸"), callback_data=LANG_ES),
            ],
        ]
    )


def build_custom_emoji_entities(
    text: str,
    emoji_ids: list[str],
    marker: str = PLACEHOLDER,
) -> list[MessageEntity]:
    entities: list[MessageEntity] = []
    search_from = 0

    for emoji_id in emoji_ids:
        if not emoji_id:
            continue

        idx = text.find(marker, search_from)
        if idx == -1:
            break

        entities.append(
            MessageEntity(
                type="custom_emoji",
                offset=idx,
                length=1,
                custom_emoji_id=emoji_id,
            )
        )
        search_from = idx + 1

    return entities


def build_ad_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[str, Optional[str]]:
    form_text = context.user_data.get("ad_form_text", "").strip()

    header = (
        f"ðŸ‘¤ {display_plain_name(update)}\n\n"
    )

    caption = header + form_text
    if len(caption) <= 1024:
        return caption, None

    available_for_form = max(0, 1024 - len(header))
    clipped_form = form_text[:available_for_form]
    remainder = form_text[available_for_form:]

    return header + clipped_form, remainder or None


def build_sale_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    return (
        "âš¡ SALE REQUEST\n"
        "Status: Pending review\n"
        "---------------------------------\n"
        f"ðŸ‘¤ User: {display_name(update)}\n"
        f"ðŸ†” User ID: {user_id_str(update)}\n"
        f"ðŸ“¦ Package: {context.user_data.get('sale_plan_label', 'N/A')}\n"
        f"ðŸ’³ Payment Method: {context.user_data.get('payment_method_label', 'N/A')}\n"
        f"ðŸ§¾ Payment Detail: {context.user_data.get('payment_detail', 'N/A')}\n"
    )


def build_request_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    requested_items = context.user_data.get("requested_items", "N/A")
    budget = context.user_data.get("budget", "N/A")
    return (
        "ðŸ›’ Your purchase request summary:\n\n"
        f"ðŸŽ¯ Requested skins and guns: {requested_items}\n"
        f"ðŸ’° Budget: {budget}\n\n"
        "Would you like to send this request to admin for review?"
    )


def build_request_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    requested_items = context.user_data.get("requested_items", "N/A")
    budget = context.user_data.get("budget", "N/A")
    return (
        "ðŸ›’ ACCOUNT REQUEST\n"
        "Status: Pending review\n"
        "---------------------------------\n"
        f"ðŸ‘¤ {display_plain_name(update)}\n"
        f"ðŸŽ¯ Requested skins and guns: {requested_items}\n"
        f"ðŸ’° Budget: {budget}\n"
    )


def build_support_text(context: ContextTypes.DEFAULT_TYPE | None = None) -> tuple[str, list[MessageEntity]]:
    text = (
        f"{PLACEHOLDER} {tr(context, 'Support')}\n\n"
        f"{tr(context, 'Please click the button below.')}"
    )
    entities = build_custom_emoji_entities(text, [SUPPORT_HEADER_EMOJI_ID])
    return text, entities


def build_account_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple[str, list[MessageEntity]]:
    user = update.effective_user
    username = f"@{user.username}" if user and user.username else "No username"
    total_orders = context.user_data.get("total_orders", 0)
    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    text = (
        f"{PLACEHOLDER} {tr(context, 'Your Account:')}\n\n"
        f"{tr(context, 'User ID')}: {user.id if user else 'N/A'}\n"
        f"{tr(context, 'Your Username')}: {username}\n"
        f"{tr(context, 'Account Status')}: {tr(context, 'Verified')}\n"
        f"{tr(context, 'Total Orders')}: {total_orders}\n\n"
        f"{PLACEHOLDER} {tr(context, 'Account Balance')}: 0$\n\n"
        f"{PLACEHOLDER} {tr(context, 'Time')}: {now_text}"
    )
    entities = build_custom_emoji_entities(
        text,
        [
            ACCOUNT_HEADER_EMOJI_ID,
            ACCOUNT_BALANCE_EMOJI_ID,
            ACCOUNT_TIME_EMOJI_ID,
        ],
    )
    return text, entities


def build_language_text(context: ContextTypes.DEFAULT_TYPE | None = None) -> tuple[str, list[MessageEntity]]:
    text = (
        f"{PLACEHOLDER} {tr(context, 'Change Language')}\n"
        f"{tr(context, 'Please select your preferred language from the list below.')}"
    )
    entities = build_custom_emoji_entities(text, [LANGUAGE_HEADER_EMOJI_ID])
    return text, entities


async def send_support_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    if SUPPORT_STICKER_FILE_ID:
        try:
            await context.bot.send_sticker(
                chat_id=chat_id,
                sticker=SUPPORT_STICKER_FILE_ID,
            )
        except Exception:
            logger.exception("Failed to send support sticker")

    text, entities = build_support_text(context)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            entities=entities if entities else None,
            reply_markup=support_inline_keyboard(context),
        )
    except Exception:
        logger.exception("Failed to send support content")


async def send_account_page(update: Update, context: 
