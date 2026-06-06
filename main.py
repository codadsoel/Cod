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

BACK_MENU_TEXT = "🔙 Main Menu"
CANCEL_TEXT = "Cancel"

MENU_AUTO_AD = "Auto ad posting"
MENU_SUPPORT = "Support"
MENU_ACCOUNT = "Account"
MENU_FAST_SALE = "Fast sale"
MENU_REQUEST_ACCOUNT = "Request Account"
MENU_LANGUAGE = "Language"

PLACEHOLDER = "◻"

AD_FORM_TEMPLATE = (
    "🔗 | Synced on:\n\n"
    "📤| Description:\n\n"
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
                    tr(context, "📋 Copy Form"),
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
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text=build_main_menu_text(context),
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
                InlineKeyboardButton("✅ Approve", callback_data=f"{AD_APPROVE_PREFIX}{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{AD_REJECT_PREFIX}{request_id}"),
            ]
        ]
    )


def build_admin_request_review_keyboard(request_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"{REQ_APPROVE_PREFIX}{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{REQ_REJECT_PREFIX}{request_id}"),
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
                InlineKeyboardButton(tr(context, "Chinese 🇨🇳"), callback_data=LANG_ZH),
                InlineKeyboardButton(tr(context, "Hindi 🇮🇳"), callback_data=LANG_HI),
            ],
            [
                InlineKeyboardButton(tr(context, "Russian 🇷🇺"), callback_data=LANG_RU),
                InlineKeyboardButton(tr(context, "Farsi 🇮🇷"), callback_data=LANG_FA),
            ],
            [
                InlineKeyboardButton(tr(context, "English 🇺🇸"), callback_data=LANG_EN),
                InlineKeyboardButton(tr(context, "Arabic 🇸🇦"), callback_data=LANG_AR),
            ],
            [
                InlineKeyboardButton(tr(context, "Hebrew 🇮🇱"), callback_data=LANG_HE),
                InlineKeyboardButton(tr(context, "Uzbekcha 🇺🇿"), callback_data=LANG_UZ),
            ],
            [
                InlineKeyboardButton(tr(context, "Italiano 🇮🇹"), callback_data=LANG_IT),
                InlineKeyboardButton(tr(context, "Turkce 🇹🇷"), callback_data=LANG_TR),
            ],
            [
                InlineKeyboardButton(tr(context, "French 🇫🇷"), callback_data=LANG_FR),
                InlineKeyboardButton(tr(context, "Spanish 🇪🇸"), callback_data=LANG_ES),
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
        f"👤 {display_plain_name(update)}\n\n"
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
        "⚡ SALE REQUEST\n"
        "Status: Pending review\n"
        "---------------------------------\n"
        f"👤 User: {display_name(update)}\n"
        f"🆔 User ID: {user_id_str(update)}\n"
        f"📦 Package: {context.user_data.get('sale_plan_label', 'N/A')}\n"
        f"💳 Payment Method: {context.user_data.get('payment_method_label', 'N/A')}\n"
        f"🧾 Payment Detail: {context.user_data.get('payment_detail', 'N/A')}\n"
    )


def build_request_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    requested_items = context.user_data.get("requested_items", "N/A")
    budget = context.user_data.get("budget", "N/A")
    template = tr(
        context,
        "🛒 Your purchase request summary:\n\n"
        "🎯 Requested skins and guns: {items}\n"
        "💰 Budget: {budget}\n\n"
        "Would you like to send this request to admin for review?"
    )
    return template.format(items=requested_items, budget=budget)


def build_request_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    requested_items = context.user_data.get("requested_items", "N/A")
    budget = context.user_data.get("budget", "N/A")
    return (
        "🛒 ACCOUNT REQUEST\n"
        "Status: Pending review\n"
        "---------------------------------\n"
        f"👤 {display_plain_name(update)}\n"
        f"🎯 Requested skins and guns: {requested_items}\n"
        f"💰 Budget: {budget}\n"
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


async def send_account_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    context.user_data.setdefault("total_orders", 0)
    text, entities = build_account_text(update, context)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            entities=entities if entities else None,
            reply_markup=account_inline_keyboard(context),
        )
    except Exception:
        logger.exception("Failed to send account page")


async def send_language_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    text, entities = build_language_text(context)

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            entities=entities if entities else None,
            reply_markup=language_inline_keyboard(context),
        )
    except Exception:
        logger.exception("Failed to send language page")


async def handle_menu_shortcuts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    msg = update.effective_message
    if not msg:
        return None

    text = (msg.text or "").strip()

    if button_text_matches(context, text, BACK_MENU_TEXT):
        await msg.reply_text(tr(context, "Back to main menu."), reply_markup=main_menu_keyboard(context))
        return MAIN_MENU

    if button_text_matches(context, text, CANCEL_TEXT):
        return await cancel(update, context)

    if button_text_matches(context, text, MENU_FAST_SALE):
        reset_flow(context)
        await msg.reply_text(
            tr(
                context,
                (
                    "Fast sale helps your listing get more attention and better visibility.\n\n"
                    "VIP ads include premium emojis, promotional hashtags, and a polished look. "
                    "Free ads are plain video + text only, with no special emojis or hashtags.\n\n"
                    "5 USD Package:\n"
                    "• Featured posting\n"
                    "• 24-hour pin\n"
                    "• Higher priority than regular listings\n\n"
                    "10 USD Package:\n"
                    "• Featured posting\n"
                    "• 48-hour pin\n"
                    "• Premium placement\n"
                    "• More visibility\n\n"
                    "Choose a package:"
                ),
            ),
            reply_markup=sale_plan_keyboard(context),
        )
        return SALE_PLAN

    if button_text_matches(context, text, MENU_AUTO_AD):
        reset_flow(context)
        await msg.reply_text(
            tr(context, "Send a short video of the account. Maximum 2 minutes."),
            reply_markup=nav_keyboard(context),
        )
        return AD_VIDEO

    if button_text_matches(context, text, MENU_REQUEST_ACCOUNT):
        reset_flow(context)
        await msg.reply_text(
            tr(context, "Type the skins and guns you want inside the account."),
            reply_markup=nav_keyboard(context),
        )
        return REQUEST_ITEMS

    if button_text_matches(context, text, MENU_SUPPORT):
        reset_flow(context)
        await send_support_content(update, context)
        return MAIN_MENU

    if button_text_matches(context, text, MENU_ACCOUNT):
        reset_flow(context)
        await send_account_page(update, context)
        return ACCOUNT_VIEW

    if button_text_matches(context, text, MENU_LANGUAGE):
        reset_flow(context)
        await send_language_page(update, context)
        await send_main_menu_page(update, context)
        return LANGUAGE_VIEW

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_flow(context)
    await send_main_menu_page(update, context)
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_flow(context)
    await send_main_menu_page(update, context)
    return MAIN_MENU


async def main_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    await update.message.reply_text(
        tr(context, "Please choose one of the menu options."),
        reply_markup=main_menu_keyboard(context),
    )
    return MAIN_MENU


async def account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == ACCOUNT_TOTAL_ORDERS:
        total_orders = context.user_data.get("total_orders", 0)
        await query.message.reply_text(
            f"Total Orders: {total_orders}",
            reply_markup=account_inline_keyboard(context),
        )
        return


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    mapping = {
        LANG_ZH: "Chinese",
        LANG_HI: "Hindi",
        LANG_RU: "Russian",
        LANG_FA: "Persian",
        LANG_EN: "English",
        LANG_AR: "Arabic",
        LANG_HE: "Hebrew",
        LANG_UZ: "Uzbekcha",
        LANG_IT: "Italiano",
        LANG_TR: "Turkish",
        LANG_FR: "French",
        LANG_ES: "Spanish",
    }

    chosen = mapping.get(query.data)
    if not chosen:
        return

    context.user_data["language"] = chosen
    context.user_data["language_code"] = query.data

    # Refresh both pages immediately so the new language is visible at once.
    await send_language_page(update, context)
    await send_main_menu_page(update, context)


async def ad_video_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    video = update.message.video
    if video is None:
        await update.message.reply_text(
            tr(context, "Please send only a video."),
            reply_markup=nav_keyboard(context),
        )
        return AD_VIDEO

    if video.duration is None:
        await update.message.reply_text(
            tr(context, "Video duration could not be detected. Please send a normal video."),
            reply_markup=nav_keyboard(context),
        )
        return AD_VIDEO

    if video.duration > 120:
        await update.message.reply_text(
            tr(context, "Video duration must be at most 2 minutes. Please send it again."),
            reply_markup=nav_keyboard(context),
        )
        return AD_VIDEO

    context.user_data["video_file_id"] = video.file_id
    context.user_data["video_duration"] = video.duration

    await update.message.reply_text(
        tr(context, "Copy the form below, fill it out, and send it back here:"),
        reply_markup=nav_keyboard(context),
    )
    await update.message.reply_text(
        AD_FORM_TEMPLATE,
        reply_markup=ad_form_keyboard(context),
    )
    return AD_FORM


async def ad_form_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "The form text cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return AD_FORM

    context.user_data["ad_form_text"] = text

    preview = tr(context, "Ad preview:\n\n{text}\n\nDo you confirm this ad?").format(text=text)
    await update.message.reply_text(preview, reply_markup=ad_confirm_keyboard(context))
    return AD_CONFIRM


async def ad_confirm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == AD_CONFIRM_NO:
        reset_flow(context)
        await query.message.reply_text(
            tr(context, "Ad cancelled."),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

    if query.data == AD_CONFIRM_YES:
        video_file_id = context.user_data.get("video_file_id")
        if not video_file_id:
            reset_flow(context)
            await query.message.reply_text(
                tr(context, "Video not found. Please start again."),
                reply_markup=main_menu_keyboard(context),
            )
            return MAIN_MENU

        caption, extra_text = build_ad_caption(update, context)
        request_id = uuid4().hex[:8]

        pending_ads = context.application.bot_data.setdefault("pending_ads", {})
        pending_ads[request_id] = {
            "video_file_id": video_file_id,
            "caption": caption,
            "extra_text": extra_text,
            "user_id": update.effective_user.id if update.effective_user else None,
        }

        try:
            await context.bot.send_video(
                chat_id=ADMIN_GROUP_ID,
                video=video_file_id,
                caption=caption,
                reply_markup=build_admin_ad_review_keyboard(request_id),
            )
            if extra_text:
                await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=extra_text,
                )
        except Exception:
            logger.exception("Failed to send ad review to admin group")

        await query.message.reply_text(
            tr(context, "Your ad has been sent for admin review."),
            reply_markup=main_menu_keyboard(context),
        )
        reset_flow(context)
        return MAIN_MENU

    await query.message.reply_text(
        tr(context, "Please choose one of the options."),
        reply_markup=ad_confirm_keyboard(context),
    )
    return AD_CONFIRM


async def admin_ad_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith(AD_APPROVE_PREFIX):
        action = "approve"
        request_id = data[len(AD_APPROVE_PREFIX):]
    elif data.startswith(AD_REJECT_PREFIX):
        action = "reject"
        request_id = data[len(AD_REJECT_PREFIX):]
    else:
        return

    pending_ads = context.application.bot_data.get("pending_ads", {})
    pending = pending_ads.pop(request_id, None)
    if not pending:
        await query.message.reply_text(tr(context, "This ad request is no longer available."))
        return

    user_id = pending.get("user_id")
    caption = pending.get("caption", "")
    extra_text = pending.get("extra_text")

    if action == "reject":
        try:
            if query.message:
                await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await query.message.reply_text(tr(context, "Ad rejected."))
        if user_id:
            try:
                await context.bot.send_message(chat_id=user_id, text="Your ad was rejected by admin.")
            except Exception:
                logger.exception("Failed to notify user about rejection")
        return

    try:
        await context.bot.send_video(
            chat_id=get_ad_channel_target(),
            video=pending["video_file_id"],
            caption=caption,
        )
        if extra_text:
            await context.bot.send_message(
                chat_id=get_ad_channel_target(),
                text=extra_text,
            )
    except Exception:
        logger.exception("Failed to post approved ad to channel")
        await query.message.reply_text(tr(context, "Failed to post ad to channel."))
        return

    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await query.message.reply_text(tr(context, "Ad approved and posted to channel."))
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Your ad was approved and posted to the channel.",
            )
        except Exception:
            logger.exception("Failed to notify user about approval")


async def admin_request_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith(REQ_APPROVE_PREFIX):
        action = "approve"
        request_id = data[len(REQ_APPROVE_PREFIX):]
    elif data.startswith(REQ_REJECT_PREFIX):
        action = "reject"
        request_id = data[len(REQ_REJECT_PREFIX):]
    else:
        return

    pending_requests = context.application.bot_data.get("pending_requests", {})
    pending = pending_requests.pop(request_id, None)
    if not pending:
        await query.message.reply_text(tr(context, "This request is no longer available."))
        return

    user_id = pending.get("user_id")

    if action == "reject":
        try:
            if query.message:
                await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await query.message.reply_text(tr(context, "Request rejected."))
        if user_id:
            try:
                await context.bot.send_message(chat_id=user_id, text="Your request was rejected by admin.")
            except Exception:
                logger.exception("Failed to notify user about request rejection")
        return

    try:
        requested_items = pending.get("requested_items", "N/A")
        budget = pending.get("budget", "N/A")
        plain_name = pending.get("plain_name", "Unknown User")

        text = (
            "🛒 ACCOUNT REQUEST\n"
            "Status: Pending review\n"
            "---------------------------------\n"
            f"👤 {plain_name}\n"
            f"🎯 Requested skins and guns: {requested_items}\n"
            f"💰 Budget: {budget}\n"
        )

        await context.bot.send_message(
            chat_id=get_ad_channel_target(),
            text=text,
        )
    except Exception:
        logger.exception("Failed to post approved request to channel")
        await query.message.reply_text(tr(context, "Failed to post request to channel."))
        return

    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await query.message.reply_text(tr(context, "Request approved and posted to channel."))
    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="Your request was approved and posted to the channel.",
            )
        except Exception:
            logger.exception("Failed to notify user about request approval")



async def sale_plan_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == PLAN_5:
        context.user_data["sale_plan_label"] = "5 USD"
        context.user_data["sale_plan_price"] = 5
    elif query.data == PLAN_10:
        context.user_data["sale_plan_label"] = "10 USD"
        context.user_data["sale_plan_price"] = 10
    else:
        await query.message.reply_text(
            tr(context, "Please choose a package."),
            reply_markup=sale_plan_keyboard(context),
        )
        return SALE_PLAN

    await query.message.reply_text(
        tr(context, "Choose a payment method:"),
        reply_markup=payment_method_keyboard(context),
    )
    return SALE_PAYMENT_METHOD


async def sale_payment_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == PAY_CRYPTO:
        context.user_data["payment_method_label"] = "USDT BEP20"
        await query.message.reply_text(
            "Crypto payment selected.\n\n"
            "Network: USDT BEP20\n"
            f"Payment address:\n{USDT_BEP20_ADDRESS}\n\n"
            "After payment, send the TXID or transaction hash here.",
            reply_markup=nav_keyboard(context),
        )
        return SALE_CRYPTO_TXID

    if query.data == PAY_GIFTCARD:
        context.user_data["payment_method_label"] = "Binance Gift Card"
        await query.message.reply_text(
            tr(context, "Send the Binance Gift Card code here."),
            reply_markup=nav_keyboard(context),
        )
        return SALE_GIFT_CODE

    await query.message.reply_text(
        tr(context, "Please choose one of the payment methods."),
        reply_markup=payment_method_keyboard(context),
    )
    return SALE_PAYMENT_METHOD


async def sale_crypto_txid_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "TXID cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return SALE_CRYPTO_TXID

    context.user_data["payment_detail"] = f"TXID / Hash: {text}"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=build_sale_text(update, context),
        )
    except Exception:
        logger.exception("Failed to send crypto sale info to group")

    await update.message.reply_text(
        tr(context, "Pending review."),
        reply_markup=main_menu_keyboard(context),
    )
    reset_flow(context)
    return MAIN_MENU


async def sale_gift_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "Gift card code cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return SALE_GIFT_CODE

    context.user_data["payment_detail"] = f"Gift Card Code: {text}"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=build_sale_text(update, context),
        )
    except Exception:
        logger.exception("Failed to send gift card sale info to group")

    await update.message.reply_text(
        tr(context, "Pending review."),
        reply_markup=main_menu_keyboard(context),
    )
    reset_flow(context)
    return MAIN_MENU


async def request_items_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "The requested items cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return REQUEST_ITEMS

    context.user_data["requested_items"] = text

    await update.message.reply_text(
        tr(context, "What is your budget?"),
        reply_markup=nav_keyboard(context),
    )
    return REQUEST_BUDGET


async def request_budget_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "Budget cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return REQUEST_BUDGET

    context.user_data["budget"] = text

    await update.message.reply_text(
        build_request_summary(update, context),
        reply_markup=request_confirm_keyboard(context),
    )
    return REQUEST_CONFIRM


async def request_confirm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == REQ_CONFIRM_NO:
        reset_flow(context)
        await query.message.reply_text(
            tr(context, "Request cancelled."),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

    if query.data == REQ_CONFIRM_YES:
        request_id = uuid4().hex[:8]
        pending_requests = context.application.bot_data.setdefault("pending_requests", {})
        pending_requests[request_id] = {
            "requested_items": context.user_data.get("requested_items", "N/A"),
            "budget": context.user_data.get("budget", "N/A"),
            "user_id": update.effective_user.id if update.effective_user else None,
            "plain_name": display_plain_name(update),
        }

        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=build_request_admin_text(update, context),
                reply_markup=build_admin_request_review_keyboard(request_id),
            )
        except Exception:
            logger.exception("Failed to send account request to group")

        await query.message.reply_text(
            tr(context, "Your request has been sent to admin for review."),
            reply_markup=main_menu_keyboard(context),
        )
        reset_flow(context)
        return MAIN_MENU

    await query.message.reply_text(
        tr(context, "Please choose one of the options."),
        reply_markup=request_confirm_keyboard(context),
    )
    return REQUEST_CONFIRM


async def unexpected_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    await update.message.reply_text(
        tr(context, "Please use the available options."),
        reply_markup=main_menu_keyboard(context),
    )
    return MAIN_MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)


def build_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        CallbackQueryHandler(
            admin_ad_review_callback,
            pattern=f"^({AD_APPROVE_PREFIX}|{AD_REJECT_PREFIX}).+$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            admin_request_review_callback,
            pattern=f"^({REQ_APPROVE_PREFIX}|{REQ_REJECT_PREFIX}).+$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            account_callback,
            pattern=f"^({ACCOUNT_TOTAL_ORDERS})$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            language_callback,
            pattern=f"^({LANG_ZH}|{LANG_HI}|{LANG_RU}|{LANG_FA}|{LANG_EN}|{LANG_AR}|{LANG_HE}|{LANG_UZ}|{LANG_IT}|{LANG_TR}|{LANG_FR}|{LANG_ES})$",
        )
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            AD_VIDEO: [
                MessageHandler(filters.VIDEO, ad_video_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ad_video_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            AD_FORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ad_form_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            AD_CONFIRM: [
                CallbackQueryHandler(ad_confirm_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            SALE_PLAN: [
                CallbackQueryHandler(sale_plan_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            SALE_PAYMENT_METHOD: [
                CallbackQueryHandler(sale_payment_method_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            SALE_CRYPTO_TXID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sale_crypto_txid_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            SALE_GIFT_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sale_gift_code_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            REQUEST_ITEMS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_items_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            REQUEST_BUDGET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_budget_received),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            REQUEST_CONFIRM: [
                CallbackQueryHandler(request_confirm_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            ACCOUNT_VIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
            LANGUAGE_VIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, unexpected_private_message),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_error_handler(error_handler)
    return app


def main() -> None:
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("Set BOT_TOKEN in the CONFIG section.")
    if USDT_BEP20_ADDRESS == "PASTE_YOUR_USDT_BEP20_ADDRESS_HERE":
        raise RuntimeError("Set USDT_BEP20_ADDRESS in the CONFIG section.")

    app = build_application()
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
