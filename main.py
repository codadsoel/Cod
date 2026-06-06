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
from pathlib import Path
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
MENU_BUY_ACCOUNT = "Buy Account"
MENU_MY_LISTINGS = "My Listings"
MENU_SELLER_RATING = "Seller Rating"

BUY_ACCOUNT_PENDING = "buy_account_pending"
BUY_PAYMENT_PENDING = "buy_payment_pending"
BUY_DETAIL_PENDING = "buy_detail_pending"

BUY_PAY_CRYPTO = "buy_pay_crypto"
BUY_PAY_GIFTCARD = "buy_pay_giftcard"

BUY_APPROVE_PREFIX = "buy_approve_"
BUY_REJECT_PREFIX = "buy_reject_"

ADMIN_MENU_REGISTER = "admin_menu_register"
ADMIN_MENU_LIST = "admin_menu_list"
ADMIN_MENU_CLOSE = "admin_menu_close"

ADMIN_MODE_REGISTER_ACCOUNT = "admin_mode_register_account"

CC_DB_FILE: Final[Path] = Path("cc.db")
SELLER_STATS_FILE: Final[Path] = Path("seller_stats.json")

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


def ensure_data_files() -> None:
    if not CC_DB_FILE.exists():
        CC_DB_FILE.write_text("", encoding="utf-8")
    if not SELLER_STATS_FILE.exists():
        SELLER_STATS_FILE.write_text("{}", encoding="utf-8")


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_account_line(line: str) -> dict:
    raw = (line or "").strip()
    if not raw:
        return {}

    # Supports both simple one-line numbers and structured pipe-separated records.
    if "|" not in raw:
        return {
            "account_number": raw,
            "price": "",
            "title": "",
            "description": "",
            "delivery_text": "",
            "seller_id": "",
            "seller_name": "",
            "status": "available",
            "created_at": "",
            "updated_at": "",
        }

    parts = [p.strip() for p in raw.split("|")]
    while len(parts) < 10:
        parts.append("")
    return {
        "account_number": parts[0],
        "price": parts[1],
        "title": parts[2],
        "description": parts[3],
        "delivery_text": parts[4],
        "seller_id": parts[5],
        "seller_name": parts[6],
        "status": parts[7] or "available",
        "created_at": parts[8],
        "updated_at": parts[9],
    }


def _serialize_account_record(record: dict) -> str:
    fields = [
        record.get("account_number", "").strip(),
        str(record.get("price", "") or "").strip(),
        str(record.get("title", "") or "").strip(),
        str(record.get("description", "") or "").strip(),
        str(record.get("delivery_text", "") or "").strip(),
        str(record.get("seller_id", "") or "").strip(),
        str(record.get("seller_name", "") or "").strip(),
        str(record.get("status", "available") or "available").strip(),
        str(record.get("created_at", "") or "").strip(),
        str(record.get("updated_at", "") or "").strip(),
    ]
    return "|".join(fields)


def load_account_records() -> list[dict]:
    ensure_data_files()
    records: list[dict] = []
    for line in CC_DB_FILE.read_text(encoding="utf-8").splitlines():
        rec = _parse_account_line(line)
        if rec.get("account_number"):
            records.append(rec)
    return records


def save_account_records(records: list[dict]) -> None:
    ensure_data_files()
    lines = [_serialize_account_record(r) for r in records if r.get("account_number")]
    CC_DB_FILE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def find_account_record(account_number: str) -> Optional[dict]:
    target = (account_number or "").strip()
    for rec in load_account_records():
        if (rec.get("account_number") or "").strip() == target:
            return rec
    return None


def upsert_account_record(record: dict) -> dict:
    records = load_account_records()
    target = (record.get("account_number") or "").strip()
    if not target:
        raise ValueError("account_number is required")

    updated = False
    for idx, existing in enumerate(records):
        if (existing.get("account_number") or "").strip() == target:
            # preserve sold/available status if the record already exists
            merged = {**existing, **record}
            merged["account_number"] = target
            merged["updated_at"] = _now_text()
            records[idx] = merged
            updated = True
            break

    if not updated:
        record = {
            **record,
            "account_number": target,
            "status": record.get("status", "available") or "available",
            "created_at": record.get("created_at") or _now_text(),
            "updated_at": record.get("updated_at") or _now_text(),
        }
        records.append(record)

    save_account_records(records)
    return find_account_record(target) or record


def update_account_status(account_number: str, status: str) -> bool:
    records = load_account_records()
    target = (account_number or "").strip()
    changed = False
    for rec in records:
        if (rec.get("account_number") or "").strip() == target:
            rec["status"] = status
            rec["updated_at"] = _now_text()
            changed = True
            break
    if changed:
        save_account_records(records)
    return changed


def delete_account_record(account_number: str) -> bool:
    records = load_account_records()
    target = (account_number or "").strip()
    new_records = [r for r in records if (r.get("account_number") or "").strip() != target]
    if len(new_records) == len(records):
        return False
    save_account_records(new_records)
    return True


def seller_stats_load() -> dict:
    ensure_data_files()
    try:
        return json.loads(SELLER_STATS_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def seller_stats_save(data: dict) -> None:
    ensure_data_files()
    SELLER_STATS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def seller_stats_update_on_sale(seller_id: str, seller_name: str) -> None:
    if not seller_id:
        return
    data = seller_stats_load()
    entry = data.get(seller_id, {"sold": 0, "name": seller_name or ""})
    entry["sold"] = int(entry.get("sold", 0)) + 1
    if seller_name:
        entry["name"] = seller_name
    data[seller_id] = entry
    seller_stats_save(data)


def seller_rank_from_sold(sold_count: int) -> str:
    if sold_count <= 0:
        return "Bronze"
    if sold_count < 5:
        return "Bronze"
    if sold_count < 15:
        return "Silver"
    return "Gold"


def format_account_record(record: dict) -> str:
    account_number = record.get("account_number", "N/A")
    title = record.get("title", "")
    price = record.get("price", "")
    description = record.get("description", "")
    status = record.get("status", "available")
    seller_name = record.get("seller_name", "")
    lines = [
        f"• {account_number}",
        f"  Status: {status}",
    ]
    if title:
        lines.append(f"  Title: {title}")
    if price:
        lines.append(f"  Price: {price}")
    if description:
        lines.append(f"  Description: {description}")
    if seller_name:
        lines.append(f"  Seller: {seller_name}")
    return "\n".join(lines)


def get_my_listings_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    uid = str(update.effective_user.id if update.effective_user else "")
    my_records = [r for r in load_account_records() if str(r.get("seller_id", "")).strip() == uid]
    if not my_records:
        return tr(context, "You have not registered any accounts yet.")

    header = tr(context, "My Listings")
    lines = [f"{header} ({len(my_records)})", "---------------------------------"]
    for idx, record in enumerate(my_records, start=1):
        lines.append(f"{idx}. {format_account_record(record)}")
    return "\n".join(lines)


def get_seller_rating_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    uid = str(update.effective_user.id if update.effective_user else "")
    stats = seller_stats_load().get(uid, {"sold": 0, "name": display_plain_name(update)})
    sold = int(stats.get("sold", 0) or 0)
    rank = seller_rank_from_sold(sold)
    if sold <= 0:
        return tr(context, "You have no completed deals yet. Your rank is Bronze.")
    return (
        f"{tr(context, 'Seller Rating')}\n"
        f"---------------------------------\n"
        f"Name: {stats.get('name') or display_plain_name(update)}\n"
        f"Completed deals: {sold}\n"
        f"Rank: {rank}"
    )


def build_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Register Account", callback_data=ADMIN_MENU_REGISTER),
                InlineKeyboardButton("📄 My Listings", callback_data=ADMIN_MENU_LIST),
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data=ADMIN_MENU_CLOSE),
            ],
        ]
    )


def build_buy_payment_keyboard(context: ContextTypes.DEFAULT_TYPE | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(tr(context, "USDT BEP20"), callback_data=BUY_PAY_CRYPTO),
                InlineKeyboardButton(tr(context, "Binance Gift Card"), callback_data=BUY_PAY_GIFTCARD),
            ]
        ]
    )


def build_buy_order_admin_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"{BUY_APPROVE_PREFIX}{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{BUY_REJECT_PREFIX}{order_id}"),
            ]
        ]
    )


def build_buy_order_admin_text(order: dict) -> str:
    account = order.get("account_record", {})
    return (
        "🛒 BUY ACCOUNT ORDER\n"
        "Status: Pending approval\n"
        "---------------------------------\n"
        f"👤 {order.get('buyer_name', 'Unknown User')}\n"
        f"📌 Account: {account.get('account_number', 'N/A')}\n"
        f"💳 Payment: {order.get('payment_method', 'N/A')}\n"
        f"🧾 Detail: {order.get('payment_detail', 'N/A')}\n"
        f"💰 Price: {account.get('price', 'N/A')}\n"
    )


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
            MENU_BUY_ACCOUNT: tr(context, MENU_BUY_ACCOUNT),
            MENU_MY_LISTINGS: tr(context, MENU_MY_LISTINGS),
            MENU_SELLER_RATING: tr(context, MENU_SELLER_RATING),
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
            [
                menu_button(labels[MENU_BUY_ACCOUNT], ""),
                menu_button(labels[MENU_MY_LISTINGS], ""),
                menu_button(labels[MENU_SELLER_RATING], ""),
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


def buy_account_prompt_text(context: ContextTypes.DEFAULT_TYPE | None = None) -> str:
    return tr(context, "Send the account number in this format: #account_number1987")


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

    if button_text_matches(context, text, MENU_BUY_ACCOUNT):
        reset_flow(context)
        context.user_data["pending_flow"] = BUY_ACCOUNT_PENDING
        await msg.reply_text(
            buy_account_prompt_text(context),
            reply_markup=nav_keyboard(context),
        )
        return MAIN_MENU

    if button_text_matches(context, text, MENU_MY_LISTINGS):
        reset_flow(context)
        await msg.reply_text(
            get_my_listings_text(update, context),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

    if button_text_matches(context, text, MENU_SELLER_RATING):
        reset_flow(context)
        await msg.reply_text(
            get_seller_rating_text(update, context),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

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
    text = (update.message.text or "").strip() if update.message else ""

    pending_flow = context.user_data.get("pending_flow")

    if pending_flow == BUY_ACCOUNT_PENDING:
        return await buy_account_number_received(update, context)

    if pending_flow == BUY_DETAIL_PENDING:
        return await buy_payment_detail_received(update, context)

    handled = await handle_menu_shortcuts(update, context)
    if handled is not None:
        return handled

    await update.message.reply_text(
        tr(context, "Please choose one of the menu options."),
        reply_markup=main_menu_keyboard(context),
    )
    return MAIN_MENU



async def buy_account_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if button_text_matches(context, text, BACK_MENU_TEXT):
        context.user_data.pop("pending_flow", None)
        context.user_data.pop("buy_account_record", None)
        await update.message.reply_text(
            tr(context, "Back to main menu."),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

    if button_text_matches(context, text, CANCEL_TEXT):
        context.user_data.pop("pending_flow", None)
        context.user_data.pop("buy_account_record", None)
        return await cancel(update, context)

    if not text.startswith("#account_number") or len(text) <= len("#account_number"):
        await update.message.reply_text(
            tr(context, "Please send the account number in this format: #account_number1987"),
            reply_markup=nav_keyboard(context),
        )
        context.user_data["pending_flow"] = BUY_ACCOUNT_PENDING
        return MAIN_MENU

    record = find_account_record(text)
    if not record:
        await update.message.reply_text(
            tr(context, "This account is not available."),
            reply_markup=nav_keyboard(context),
        )
        context.user_data["pending_flow"] = BUY_ACCOUNT_PENDING
        return MAIN_MENU

    if str(record.get("status", "available")).lower() != "available":
        await update.message.reply_text(
            tr(context, "This account is already reserved or sold."),
            reply_markup=nav_keyboard(context),
        )
        context.user_data["pending_flow"] = BUY_ACCOUNT_PENDING
        return MAIN_MENU

    context.user_data["buy_account_record"] = record
    context.user_data["buy_account_number"] = text
    context.user_data["pending_flow"] = BUY_PAYMENT_PENDING

    price = record.get("price") or "N/A"
    title = record.get("title") or ""
    description = record.get("description") or ""

    availability_text = (
        "✅ Available\n"
        f"📌 Account: {text}\n"
        f"💰 Price: {price}\n"
    )
    if title:
        availability_text += f"🏷 Title: {title}\n"
    if description:
        availability_text += f"📝 Description: {description}\n"

    await update.message.reply_text(
        availability_text + "\n" + tr(context, "Choose a payment method:"),
        reply_markup=build_buy_payment_keyboard(context),
    )
    return MAIN_MENU


async def buy_payment_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if context.user_data.get("pending_flow") != BUY_PAYMENT_PENDING:
        await query.message.reply_text(tr(context, "Please use the available options."))
        return

    record = context.user_data.get("buy_account_record")
    if not record:
        await query.message.reply_text(tr(context, "This account is no longer available."))
        return

    data = query.data or ""
    if data == BUY_PAY_CRYPTO:
        context.user_data["buy_payment_method"] = "USDT BEP20"
        context.user_data["pending_flow"] = BUY_DETAIL_PENDING
        update_account_status(record["account_number"], "reserved")
        await query.message.reply_text(
            "Crypto payment selected.\n\n"
            "Network: USDT BEP20\n"
            f"Payment address:\n{USDT_BEP20_ADDRESS}\n\n"
            "After payment, send the TXID or transaction hash here.",
            reply_markup=nav_keyboard(context),
        )
        return

    if data == BUY_PAY_GIFTCARD:
        context.user_data["buy_payment_method"] = "Binance Gift Card"
        context.user_data["pending_flow"] = BUY_DETAIL_PENDING
        update_account_status(record["account_number"], "reserved")
        await query.message.reply_text(
            tr(context, "Send the Binance Gift Card code here."),
            reply_markup=nav_keyboard(context),
        )
        return

    await query.message.reply_text(
        tr(context, "Please choose one of the payment methods."),
        reply_markup=build_buy_payment_keyboard(context),
    )


async def buy_payment_detail_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text(
            tr(context, "Payment detail cannot be empty."),
            reply_markup=nav_keyboard(context),
        )
        return MAIN_MENU

    if button_text_matches(context, text, BACK_MENU_TEXT):
        record = context.user_data.get("buy_account_record")
        if record:
            update_account_status(record["account_number"], "available")
        context.user_data.pop("buy_account_record", None)
        context.user_data.pop("buy_account_number", None)
        context.user_data.pop("buy_payment_method", None)
        context.user_data.pop("pending_flow", None)
        await update.message.reply_text(
            tr(context, "Back to main menu."),
            reply_markup=main_menu_keyboard(context),
        )
        return MAIN_MENU

    if button_text_matches(context, text, CANCEL_TEXT):
        record = context.user_data.get("buy_account_record")
        if record:
            update_account_status(record["account_number"], "available")
        context.user_data.pop("buy_account_record", None)
        context.user_data.pop("buy_account_number", None)
        context.user_data.pop("buy_payment_method", None)
        context.user_data.pop("pending_flow", None)
        return await cancel(update, context)

    record = context.user_data.get("buy_account_record")
    if not record:
        await update.message.reply_text(tr(context, "This account is no longer available."))
        context.user_data.pop("pending_flow", None)
        return MAIN_MENU

    method = context.user_data.get("buy_payment_method", "N/A")
    context.user_data["buy_payment_detail"] = text
    order_id = uuid4().hex[:8]

    pending_orders = context.application.bot_data.setdefault("pending_buy_orders", {})
    pending_orders[order_id] = {
        "order_id": order_id,
        "buyer_id": update.effective_user.id if update.effective_user else None,
        "buyer_name": display_plain_name(update),
        "account_record": dict(record),
        "payment_method": method,
        "payment_detail": text,
    }

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=build_buy_order_admin_text(pending_orders[order_id]),
            reply_markup=build_buy_order_admin_keyboard(order_id),
        )
    except Exception:
        logger.exception("Failed to send buy order to admin group")

    await update.message.reply_text(
        tr(context, "Your payment has been sent for admin approval."),
        reply_markup=main_menu_keyboard(context),
    )

    context.user_data.pop("buy_account_record", None)
    context.user_data.pop("buy_account_number", None)
    context.user_data.pop("buy_payment_method", None)
    context.user_data.pop("buy_payment_detail", None)
    context.user_data.pop("pending_flow", None)
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



async def admin_panel_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.effective_chat
    if not chat or chat.id != ADMIN_GROUP_ID:
        if update.message:
            await update.message.reply_text(tr(context, "This command is available only in the admin group."))
        return MAIN_MENU

    context.application.bot_data["admin_mode"] = None
    await update.message.reply_text(
        "Admin Panel\n"
        "---------------------------------\n"
        "Choose an action:",
        reply_markup=build_admin_panel_keyboard(),
    )
    return MAIN_MENU


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data == ADMIN_MENU_REGISTER:
        context.application.bot_data["admin_mode"] = ADMIN_MODE_REGISTER_ACCOUNT
        await query.message.reply_text(
            "Send the account line in one of these formats:\n"
            "#account_number1987\n"
            "or\n"
            "#account_number1987 | price | title | description | delivery text",
        )
        return

    if data == ADMIN_MENU_LIST:
        records = load_account_records()
        if not records:
            await query.message.reply_text("cc.db is empty.")
        else:
            lines = ["All accounts:", "---------------------------------"]
            for idx, record in enumerate(records, start=1):
                lines.append(f"{idx}. {format_account_record(record)}")
            await query.message.reply_text("\n".join(lines))
        return

    if data == ADMIN_MENU_CLOSE:
        context.application.bot_data["admin_mode"] = None
        await query.message.reply_text("Admin panel closed.")
        return


async def admin_group_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat or chat.id != ADMIN_GROUP_ID:
        return

    mode = context.application.bot_data.get("admin_mode")
    if mode != ADMIN_MODE_REGISTER_ACCOUNT:
        return

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Send a non-empty account line.")
        return

    parts = [p.strip() for p in text.split("|")]
    while len(parts) < 5:
        parts.append("")

    account_number = parts[0]
    if not account_number.startswith("#account_number"):
        await update.message.reply_text("Invalid format. Start with #account_number...")
        return

    record = {
        "account_number": account_number,
        "price": parts[1],
        "title": parts[2],
        "description": parts[3],
        "delivery_text": parts[4],
        "seller_id": str(update.effective_user.id if update.effective_user else ""),
        "seller_name": display_plain_name(update),
        "status": "available",
        "created_at": _now_text(),
        "updated_at": _now_text(),
    }
    upsert_account_record(record)
    context.application.bot_data["admin_mode"] = None

    await update.message.reply_text(
        f"Saved to cc.db:\n{account_number}",
        reply_markup=build_admin_panel_keyboard(),
    )


async def admin_buy_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data.startswith(BUY_APPROVE_PREFIX):
        action = "approve"
        order_id = data[len(BUY_APPROVE_PREFIX):]
    elif data.startswith(BUY_REJECT_PREFIX):
        action = "reject"
        order_id = data[len(BUY_REJECT_PREFIX):]
    else:
        return

    pending_orders = context.application.bot_data.get("pending_buy_orders", {})
    order = pending_orders.pop(order_id, None)
    if not order:
        await query.message.reply_text(tr(context, "This request is no longer available."))
        return

    account = order.get("account_record", {})
    account_number = account.get("account_number", "")
    buyer_id = order.get("buyer_id")
    buyer_name = order.get("buyer_name", "Unknown User")
    seller_id = str(account.get("seller_id", ""))
    seller_name = account.get("seller_name", "")

    if action == "reject":
        update_account_status(account_number, "available")
        try:
            if query.message:
                await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text("Buy order rejected.")
        if buyer_id:
            try:
                await context.bot.send_message(
                    chat_id=buyer_id,
                    text="Your purchase request was rejected by admin.",
                )
            except Exception:
                logger.exception("Failed to notify buyer about rejection")
        return

    # approve
    delete_account_record(account_number)
    seller_stats_update_on_sale(seller_id, seller_name)

    delivery_text = account.get("delivery_text") or "Your account has been approved. Delivery will be sent shortly."
    try:
        if buyer_id:
            await context.bot.send_message(
                chat_id=buyer_id,
                text=(
                    f"✅ Approved\n"
                    f"📌 Account: {account_number}\n\n"
                    f"{delivery_text}"
                ),
            )
    except Exception:
        logger.exception("Failed to notify buyer about approval")

    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await query.message.reply_text("Buy order approved and account closed from cc.db.")


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

    app.add_handler(CommandHandler("admin", admin_panel_start))
    app.add_handler(
        CallbackQueryHandler(
            admin_panel_callback,
            pattern=f"^({ADMIN_MENU_REGISTER}|{ADMIN_MENU_LIST}|{ADMIN_MENU_CLOSE})$",
        )
    )
    app.add_handler(
        MessageHandler(
            filters.Chat(ADMIN_GROUP_ID) & filters.TEXT & ~filters.COMMAND,
            admin_group_text_router,
        )
    )
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
            admin_buy_order_callback,
            pattern=f"^({BUY_APPROVE_PREFIX}|{BUY_REJECT_PREFIX}).+$",
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            buy_payment_method_choice,
            pattern=f"^({BUY_PAY_CRYPTO}|{BUY_PAY_GIFTCARD})$",
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

    ensure_data_files()

    app = build_application()
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
