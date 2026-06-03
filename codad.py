# bot.py
# pip install -U python-telegram-bot

import logging
from typing import Final, Optional, Tuple

from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
) = range(11)

AD_CONFIRM_YES = "ad_confirm_yes"
AD_CONFIRM_NO = "ad_confirm_no"

PLAN_5 = "plan_5"
PLAN_10 = "plan_10"

PAY_CRYPTO = "pay_crypto"
PAY_GIFTCARD = "pay_giftcard"

REQ_CONFIRM_YES = "req_confirm_yes"
REQ_CONFIRM_NO = "req_confirm_no"

BACK_MENU_TEXT = "🔙 Main Menu"
CANCEL_TEXT = "Cancel"

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
    context.user_data.clear()


def display_name(update: Update) -> str:
    user = update.effective_user
    if not user:
        return "Unknown User"
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "No username"
    return f"{full_name} ({username})"


def user_id_str(update: Update) -> str:
    user = update.effective_user
    return str(user.id) if user else "N/A"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📝 Auto Ad Posting"],
            ["⚡ Fast Sale"],
            ["🛒 Request Account"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def nav_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BACK_MENU_TEXT],
            [CANCEL_TEXT],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def ad_form_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📋 Copy Form",
                    copy_text=CopyTextButton(text=AD_FORM_TEMPLATE),
                )
            ]
        ]
    )


def ad_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm & Send", callback_data=AD_CONFIRM_YES),
                InlineKeyboardButton("Cancel", callback_data=AD_CONFIRM_NO),
            ]
        ]
    )


def sale_plan_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("5 USD Package", callback_data=PLAN_5)],
            [InlineKeyboardButton("10 USD Package", callback_data=PLAN_10)],
        ]
    )


def payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("USDT BEP20", callback_data=PAY_CRYPTO)],
            [InlineKeyboardButton("Binance Gift Card", callback_data=PAY_GIFTCARD)],
        ]
    )


def request_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Send to Admin", callback_data=REQ_CONFIRM_YES),
                InlineKeyboardButton("Cancel", callback_data=REQ_CONFIRM_NO),
            ]
        ]
    )


def clip_text(text: str, limit: int) -> Tuple[str, Optional[str]]:
    if len(text) <= limit:
        return text, None
    if limit <= 3:
        return text[:limit], text[limit:]
    return text[: limit - 3] + "...", text[limit - 3 :]


def build_ad_caption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[str, Optional[str]]:
    user = update.effective_user
    form_text = context.user_data.get("ad_form_text", "").strip()

    header = (
        f"👤 User: {display_name(update)}\n"
        f"🆔 User ID: {user.id if user else 'N/A'}\n\n"
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
    return (
        "🛒 Your purchase request summary:\n\n"
        f"🎯 Requested skins and guns: {requested_items}\n"
        f"💰 Budget: {budget}\n\n"
        "Would you like to send this request to admin for review?"
    )


def build_request_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    requested_items = context.user_data.get("requested_items", "N/A")
    budget = context.user_data.get("budget", "N/A")
    return (
        "🛒 ACCOUNT REQUEST\n"
        "Status: Pending review\n"
        "---------------------------------\n"
        f"👤 User: {display_name(update)}\n"
        f"🆔 User ID: {user_id_str(update)}\n"
        f"🎯 Requested skins and guns: {requested_items}\n"
        f"💰 Budget: {budget}\n"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_flow(context)
    await update.message.reply_text(
        "Choose one of the options below:",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reset_flow(context)
    await update.message.reply_text(
        "Cancelled.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def main_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text == "📝 Auto Ad Posting":
        reset_flow(context)
        await update.message.reply_text(
            "Send a short video of the account. Maximum 2 minutes.",
            reply_markup=nav_keyboard(),
        )
        return AD_VIDEO

    if text == "⚡ Fast Sale":
        reset_flow(context)
        await update.message.reply_text(
            (
                "Fast sale helps your listing get more attention and better visibility.\n\n"
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
            reply_markup=sale_plan_keyboard(),
        )
        return SALE_PLAN

    if text == "🛒 Request Account":
        reset_flow(context)
        await update.message.reply_text(
            "Type the skins and guns you want inside the account.",
            reply_markup=nav_keyboard(),
        )
        return REQUEST_ITEMS

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    await update.message.reply_text(
        "Please choose one of the menu options.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def ad_video_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip() if update.message else ""

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    video = update.message.video
    if video is None:
        await update.message.reply_text(
            "Please send only a video.",
            reply_markup=nav_keyboard(),
        )
        return AD_VIDEO

    if video.duration is None:
        await update.message.reply_text(
            "Video duration could not be detected. Please send a normal video.",
            reply_markup=nav_keyboard(),
        )
        return AD_VIDEO

    if video.duration > 120:
        await update.message.reply_text(
            "Video duration must be at most 2 minutes. Please send it again.",
            reply_markup=nav_keyboard(),
        )
        return AD_VIDEO

    context.user_data["video_file_id"] = video.file_id
    context.user_data["video_duration"] = video.duration

    await update.message.reply_text(
        "Copy the form below, fill it out, and send it back here:",
        reply_markup=nav_keyboard(),
    )
    await update.message.reply_text(
        AD_FORM_TEMPLATE,
        reply_markup=ad_form_keyboard(),
    )
    return AD_FORM


async def ad_form_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    if not text:
        await update.message.reply_text(
            "The form text cannot be empty.",
            reply_markup=nav_keyboard(),
        )
        return AD_FORM

    context.user_data["ad_form_text"] = text

    preview = (
        "Ad preview:\n\n"
        f"{text}\n\n"
        "Do you confirm this ad?"
    )
    await update.message.reply_text(preview, reply_markup=ad_confirm_keyboard())
    return AD_CONFIRM


async def ad_confirm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == AD_CONFIRM_NO:
        reset_flow(context)
        await query.message.reply_text(
            "Ad cancelled.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if query.data == AD_CONFIRM_YES:
        video_file_id = context.user_data.get("video_file_id")
        if not video_file_id:
            reset_flow(context)
            await query.message.reply_text(
                "Video not found. Please start again.",
                reply_markup=main_menu_keyboard(),
            )
            return MAIN_MENU

        caption, extra_text = build_ad_caption(update, context)

        try:
            await context.bot.send_video(
                chat_id=ADMIN_GROUP_ID,
                video=video_file_id,
                caption=caption,
            )
            if extra_text:
                await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=extra_text,
                )
        except Exception:
            logger.exception("Failed to send ad to group")

        await query.message.reply_text(
            "It will be sent to the group soon.",
            reply_markup=main_menu_keyboard(),
        )
        reset_flow(context)
        return MAIN_MENU

    await query.message.reply_text(
        "Please choose one of the options.",
        reply_markup=ad_confirm_keyboard(),
    )
    return AD_CONFIRM


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
            "Please choose a package.",
            reply_markup=sale_plan_keyboard(),
        )
        return SALE_PLAN

    await query.message.reply_text(
        "Choose a payment method:",
        reply_markup=payment_method_keyboard(),
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
            reply_markup=nav_keyboard(),
        )
        return SALE_CRYPTO_TXID

    if query.data == PAY_GIFTCARD:
        context.user_data["payment_method_label"] = "Binance Gift Card"
        await query.message.reply_text(
            "Send the Binance Gift Card code here.",
            reply_markup=nav_keyboard(),
        )
        return SALE_GIFT_CODE

    await query.message.reply_text(
        "Please choose one of the payment methods.",
        reply_markup=payment_method_keyboard(),
    )
    return SALE_PAYMENT_METHOD


async def sale_crypto_txid_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    if not text:
        await update.message.reply_text(
            "TXID cannot be empty.",
            reply_markup=nav_keyboard(),
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
        "Pending review.",
        reply_markup=main_menu_keyboard(),
    )
    reset_flow(context)
    return MAIN_MENU


async def sale_gift_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    if not text:
        await update.message.reply_text(
            "Gift card code cannot be empty.",
            reply_markup=nav_keyboard(),
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
        "Pending review.",
        reply_markup=main_menu_keyboard(),
    )
    reset_flow(context)
    return MAIN_MENU


async def request_items_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    if not text:
        await update.message.reply_text(
            "The requested items cannot be empty.",
            reply_markup=nav_keyboard(),
        )
        return REQUEST_ITEMS

    context.user_data["requested_items"] = text

    await update.message.reply_text(
        "What is your budget?",
        reply_markup=nav_keyboard(),
    )
    return REQUEST_BUDGET


async def request_budget_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()

    if text in {BACK_MENU_TEXT, "Main Menu"}:
        reset_flow(context)
        await update.message.reply_text(
            "Back to main menu.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if text == CANCEL_TEXT:
        return await cancel(update, context)

    if not text:
        await update.message.reply_text(
            "Budget cannot be empty.",
            reply_markup=nav_keyboard(),
        )
        return REQUEST_BUDGET

    context.user_data["budget"] = text

    await update.message.reply_text(
        build_request_summary(update, context),
        reply_markup=request_confirm_keyboard(),
    )
    return REQUEST_CONFIRM


async def request_confirm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == REQ_CONFIRM_NO:
        reset_flow(context)
        await query.message.reply_text(
            "Request cancelled.",
            reply_markup=main_menu_keyboard(),
        )
        return MAIN_MENU

    if query.data == REQ_CONFIRM_YES:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_GROUP_ID,
                text=build_request_admin_text(update, context),
            )
        except Exception:
            logger.exception("Failed to send account request to group")

        await query.message.reply_text(
            "Your request has been sent to admin for review.",
            reply_markup=main_menu_keyboard(),
        )
        reset_flow(context)
        return MAIN_MENU

    await query.message.reply_text(
        "Please choose one of the options.",
        reply_markup=request_confirm_keyboard(),
    )
    return REQUEST_CONFIRM


async def unexpected_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Please use the available options.",
        reply_markup=main_menu_keyboard(),
    )
    return MAIN_MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception: %s", context.error)


def build_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

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
    if ADMIN_GROUP_ID == -1001234567890:
        raise RuntimeError("Set ADMIN_GROUP_ID in the CONFIG section.")
    if USDT_BEP20_ADDRESS == "PASTE_YOUR_USDT_BEP20_ADDRESS_HERE":
        raise RuntimeError("Set USDT_BEP20_ADDRESS in the CONFIG section.")

    app = build_application()
    logger.info("Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
