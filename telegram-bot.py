import os
import logging
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from fetch_and_store import run as fetch_and_store_hackathons
import backend.models
from backend.models import GuildConfig, HackathonDB, UserSubscription
from backend.db import SessionLocal
from backend.crud import (
    search_hackathons,
    get_hackathons_by_platform,
    get_upcoming_hackathons,
    subscribe_user,
    get_all_subscriptions,
    unsubscribe_user,
    update_guild_preferences,
    get_guild_config,
    pause_notifications,
    resume_notifications,
)

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# Helper function to check if user is admin
async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin in the chat."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # In private chats, user is always "admin"
    if update.effective_chat.type == 'private':
        return True
    
    # In groups, check if user is admin
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


def format_hackathon_message(hackathon):
    """Format a hackathon as a Telegram message with HTML formatting."""
    emojis = ["🎉", "🚀", "💡", "🔥", "💻", "🏆", "🌟", "⚡", "🔮", "🛠️"]
    import random
    random_emoji = random.choice(emojis)
    
    text = f"{random_emoji} <b>{hackathon.title}</b>\n\n"
    text += f"<b>Duration:</b> {hackathon.start_date.strftime('%B %d')} - {hackathon.end_date.strftime('%B %d, %Y')}\n"
    text += f"<b>Location:</b> {hackathon.location}\n"
    text += f"<b>Mode:</b> {hackathon.mode}\n"
    text += f"<b>Status:</b> {hackathon.status}\n\n"
    
    if hackathon.prize_pool:
        text += f"<b>Prizes:</b>\n{hackathon.prize_pool}\n\n"
    if hackathon.team_size:
        text += f"<b>Team Size:</b> {hackathon.team_size}\n"
    if hackathon.eligibility:
        text += f"<b>Eligibility:</b> {hackathon.eligibility}\n"
    
    # Create inline keyboard
    keyboard = []
    if hackathon.url:
        keyboard.append([InlineKeyboardButton("View Details", url=hackathon.url)])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    return text, hackathon.banner_url, reply_markup


async def send_hackathon_notifications(application, new_hackathons, target_chat=None):
    """
    Send hackathon notifications to chats.
    If target_chat is provided, send there. Otherwise, send to all configured chats.
    """
    if not new_hackathons:
        return
    
    if target_chat:
        # Send to specific chat (for manual commands)
        for hackathon in new_hackathons:
            try:
                text, photo_url, reply_markup = format_hackathon_message(hackathon)
                
                if photo_url:
                    await application.bot.send_photo(
                        chat_id=target_chat,
                        photo=photo_url,
                        caption=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                else:
                    await application.bot.send_message(
                        chat_id=target_chat,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                logger.info(f"Sent notification for hackathon '{hackathon.title}' to chat {target_chat}")
            except Exception as e:
                logger.error(f"Failed to send hackathon notification to chat {target_chat}: {e}")
    else:
        # Send to all configured chats (for scheduled task)
        db = SessionLocal()
        
        try:
            configs = db.query(GuildConfig).all()
            
            for config in configs:
                # Check if notifications are paused
                if config.notifications_paused == "true":
                    logger.info(f"Notifications are paused for chat {config.guild_id}. Skipping.")
                    continue
                
                chat_id = config.guild_id
                platforms = config.subscribed_platforms.split(",") if config.subscribed_platforms else ["all"]
                themes = config.subscribed_themes.split(",") if config.subscribed_themes else ["all"]
                
                # Send notification for each new hackathon
                for hackathon in new_hackathons:
                    # Filter by platform
                    if "all" not in platforms:
                        if not any(p.lower() in hackathon.source.lower() for p in platforms):
                            continue
                    
                    # Filter by theme
                    if "all" not in themes:
                        hack_tags = [t.lower() for t in hackathon.tags.split(",")] if hackathon.tags else []
                        match = False
                        for theme in themes:
                            theme_lower = theme.lower()
                            for tag in hack_tags:
                                if theme_lower in tag:
                                    match = True
                                    break
                            if match:
                                break
                        
                        if not match:
                            continue
                    
                    try:
                        text, photo_url, reply_markup = format_hackathon_message(hackathon)
                        
                        if photo_url:
                            await application.bot.send_photo(
                                chat_id=chat_id,
                                photo=photo_url,
                                caption=text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=reply_markup
                            )
                        else:
                            await application.bot.send_message(
                                chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=reply_markup
                            )
                        logger.info(f"Sent notification for hackathon '{hackathon.title}' to chat {chat_id}")
                    except Exception as e:
                        logger.error(f"Failed to send hackathon notification to chat {chat_id}: {e}")
        finally:
            db.close()


async def notify_subscribers(application, new_hackathons):
    """
    Check new hackathons against user subscriptions and send DMs.
    """
    if not new_hackathons:
        return
    
    db = SessionLocal()
    try:
        subscriptions = get_all_subscriptions(db)
        if not subscriptions:
            return
        
        # Map: user_id -> list of hackathons to notify
        user_notifications = {}
        
        for hackathon in new_hackathons:
            hack_tags = [t.lower() for t in hackathon.tags.split(",")] if hackathon.tags else []
            
            for sub in subscriptions:
                theme_lower = sub.theme.lower()
                is_match = False
                for tag in hack_tags:
                    if theme_lower in tag:
                        is_match = True
                        break
                
                if is_match:
                    if sub.user_id not in user_notifications:
                        user_notifications[sub.user_id] = []
                    # Avoid duplicates
                    if hackathon not in user_notifications[sub.user_id]:
                        user_notifications[sub.user_id].append(hackathon)
        
        # Send DMs
        for user_id, hacks in user_notifications.items():
            try:
                for hack in hacks:
                    text, photo_url, reply_markup = format_hackathon_message(hack)
                    alert_text = "🔔 <b>New Hackathon Alert!</b> (Matches your subscription)\n\n" + text
                    
                    if photo_url:
                        await application.bot.send_photo(
                            chat_id=user_id,
                            photo=photo_url,
                            caption=alert_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                    else:
                        await application.bot.send_message(
                            chat_id=user_id,
                            text=alert_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup
                        )
                    logger.info(f"Sent DM notification for '{hack.title}' to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to DM user {user_id}: {e}")
    finally:
        db.close()


# Command Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome_text = (
        "🎉 <b>Welcome to HackRadar!</b>\n\n"
        "I help you stay updated on the latest hackathons from multiple platforms.\n\n"
        "<b>What I can do:</b>\n"
        "• Automatic notifications from Devfolio, Devpost, Unstop & more\n"
        "• Filter by themes (AI, Blockchain, Web3, etc.)\n"
        "• Track upcoming deadlines and events\n"
        "• Search hackathons on-demand\n\n"
        "Use /help to see all available commands!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔍 Search Hackathons", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📖 Help", callback_data="help")],
        [InlineKeyboardButton("⭐ Star on GitHub", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 <b>HackRadar Commands</b>\n\n"
        "<b>🔍 Search & Browse</b>\n"
        "/search [keyword] - Search hackathons\n"
        "/upcoming [days] - Hackathons starting soon (default: 7 days)\n"
        "/platform [name] [count] - Filter by platform (default: 3)\n\n"
        "<b>🔔 Personal Alerts</b>\n"
        "/subscribe [theme] - Get DM alerts for a theme\n"
        "/unsubscribe [theme] - Stop DM alerts for a theme\n"
        "/subscriptions - View your subscriptions\n\n"
        "<b>🔧 Group Setup (Admin Only)</b>\n"
        "/setup - Configure group preferences\n"
        "/pause - Pause notifications\n"
        "/resume - Resume notifications\n\n"
        "<b>ℹ️ Info & Support</b>\n"
        "/about - About HackRadar\n"
        "/help - Show this message\n\n"
        "💡 <i>Tip: Add me to a group and run /setup to start receiving notifications!</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("⭐ Star on GitHub", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot")],
        [InlineKeyboardButton("🐛 Report Bug", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot/issues")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command."""
    about_text = (
        "🚀 <b>About HackRadar</b>\n\n"
        "HackRadar is an open-source bot that aggregates hackathons "
        "from multiple platforms and delivers personalized notifications.\n\n"
        "<b>Version:</b> 1.0.0\n"
        "<b>Platforms:</b> Devfolio, Devpost, Unstop, DoraHacks, MLH, Hack2Skill, Kaggle\n\n"
        "Made with 💙 by Spartan-71"
    )
    
    keyboard = [
        [InlineKeyboardButton("⭐ Star on GitHub", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot")],
        [InlineKeyboardButton("🐛 Report Bug", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot/issues")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        about_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a search keyword.\n\n"
            "Usage: /search [keyword]\n"
            "Example: /search AI"
        )
        return
    
    keyword = " ".join(context.args)
    await update.message.reply_text(f"🔍 Searching for hackathons matching '<b>{keyword}</b>'...", parse_mode=ParseMode.HTML)
    
    db = SessionLocal()
    try:
        results = search_hackathons(db, keyword)
    finally:
        db.close()
    
    if not results:
        await update.message.reply_text(f"❌ No hackathons found for <b>{keyword}</b>", parse_mode=ParseMode.HTML)
        return
    
    await update.message.reply_text(f"🔍 Found <b>{len(results)}</b> hackathon(s) for <b>{keyword}</b>:", parse_mode=ParseMode.HTML)
    await send_hackathon_notifications(context.application, results, target_chat=update.effective_chat.id)


async def platform_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /platform command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a platform name.\n\n"
            "Usage: /platform [name] [count]\n"
            "Example: /platform devfolio 5"
        )
        return
    
    platform_name = context.args[0]
    count = int(context.args[1]) if len(context.args) > 1 else 3
    
    await update.message.reply_text(f"🔍 Fetching hackathons from <b>{platform_name}</b>...", parse_mode=ParseMode.HTML)
    
    db = SessionLocal()
    try:
        results = get_hackathons_by_platform(db, platform_name, count)
    finally:
        db.close()
    
    if not results:
        await update.message.reply_text(f"❌ No hackathons found for platform <b>{platform_name}</b>", parse_mode=ParseMode.HTML)
        return
    
    await update.message.reply_text(f"🔍 Found <b>{len(results)}</b> hackathon(s) from <b>{platform_name}</b>:", parse_mode=ParseMode.HTML)
    await send_hackathon_notifications(context.application, results, target_chat=update.effective_chat.id)


async def upcoming_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upcoming command."""
    days = int(context.args[0]) if context.args else 7
    
    await update.message.reply_text(f"📅 Fetching hackathons starting in the next <b>{days}</b> days...", parse_mode=ParseMode.HTML)
    
    db = SessionLocal()
    try:
        results = get_upcoming_hackathons(db, days)
    finally:
        db.close()
    
    if not results:
        await update.message.reply_text(f"❌ No upcoming hackathons found in the next <b>{days}</b> days.", parse_mode=ParseMode.HTML)
        return
    
    await update.message.reply_text(f"📅 Found <b>{len(results)}</b> upcoming hackathon(s) in the next <b>{days}</b> days:", parse_mode=ParseMode.HTML)
    await send_hackathon_notifications(context.application, results, target_chat=update.effective_chat.id)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a theme to subscribe to.\n\n"
            "Usage: /subscribe [theme]\n"
            "Example: /subscribe AI"
        )
        return
    
    theme = " ".join(context.args)
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        sub, is_new = subscribe_user(db, user_id, theme)
        if is_new:
            await update.message.reply_text(f"✅ You have successfully subscribed to <b>{theme}</b> updates!", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"ℹ️ You are already subscribed to <b>{theme}</b>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error subscribing: {str(e)}")
        logger.error(f"Error in subscribe command: {e}")
    finally:
        db.close()


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unsubscribe command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a theme to unsubscribe from.\n\n"
            "Usage: /unsubscribe [theme]\n"
            "Example: /unsubscribe AI"
        )
        return
    
    theme = " ".join(context.args)
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        removed = unsubscribe_user(db, user_id, theme)
        if removed:
            await update.message.reply_text(f"✅ You have successfully unsubscribed from <b>{theme}</b> updates.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"ℹ️ You were not subscribed to <b>{theme}</b>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error unsubscribing: {str(e)}")
        logger.error(f"Error in unsubscribe command: {e}")
    finally:
        db.close()


async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscriptions command."""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        all_subs = get_all_subscriptions(db)
        user_subs = [sub for sub in all_subs if sub.user_id == user_id]
        
        if not user_subs:
            await update.message.reply_text(
                "ℹ️ You have no active subscriptions.\n\n"
                "Use /subscribe [theme] to start receiving notifications!"
            )
            return
        
        subs_text = "🔔 <b>Your Subscriptions:</b>\n\n"
        for sub in user_subs:
            subs_text += f"• {sub.theme}\n"
        
        subs_text += f"\n<i>Total: {len(user_subs)} subscription(s)</i>"
        
        await update.message.reply_text(subs_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching subscriptions: {str(e)}")
        logger.error(f"Error in subscriptions command: {e}")
    finally:
        db.close()


async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setup command (group chats only)."""
    # Check if in group chat
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "❌ This command can only be used in group chats.\n\n"
            "Add me to a group and run /setup there!"
        )
        return
    
    # Check if user is admin
    if not await is_user_admin(update, context):
        await update.message.reply_text(
            "❌ You need to be an administrator to use this command."
        )
        return
    
    # Send setup message with inline keyboard
    setup_text = (
        "⚙️ <b>HackRadar Setup</b>\n\n"
        "Please configure your preferences:\n\n"
        "1. Select platforms to track\n"
        "2. Select themes to track\n"
        "3. Confirm your selection\n\n"
        "💡 <i>Leave selections empty to receive all notifications.</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("📱 Select Platforms", callback_data="setup_platforms")],
        [InlineKeyboardButton("🎯 Select Themes", callback_data="setup_themes")],
        [InlineKeyboardButton("✅ Save Preferences", callback_data="setup_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="setup_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Initialize setup state in context
    context.chat_data['setup_platforms'] = []
    context.chat_data['setup_themes'] = []
    
    await update.message.reply_text(
        setup_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pause command."""
    # Check if in group chat
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "❌ This command can only be used in group chats."
        )
        return
    
    # Check if user is admin
    if not await is_user_admin(update, context):
        await update.message.reply_text(
            "❌ You need to be an administrator to use this command."
        )
        return
    
    db = SessionLocal()
    try:
        success = pause_notifications(db, str(update.effective_chat.id))
        if success:
            await update.message.reply_text(
                "⏸️ <b>Notifications Paused</b>\n\n"
                "Hackathon notifications have been paused for this group.\n\n"
                "Use /resume to start receiving notifications again.",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "❌ <b>Setup Required</b>\n\n"
                "Please run /setup first to configure the bot before using this command.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error pausing notifications: {str(e)}")
        logger.error(f"Error in pause command: {e}")
    finally:
        db.close()


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command."""
    # Check if in group chat
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "❌ This command can only be used in group chats."
        )
        return
    
    # Check if user is admin
    if not await is_user_admin(update, context):
        await update.message.reply_text(
            "❌ You need to be an administrator to use this command."
        )
        return
    
    db = SessionLocal()
    try:
        success = resume_notifications(db, str(update.effective_chat.id))
        if success:
            await update.message.reply_text(
                "▶️ <b>Notifications Resumed</b>\n\n"
                "Hackathon notifications have been resumed for this group.\n\n"
                "You'll start receiving updates again.",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "❌ <b>Setup Required</b>\n\n"
                "Please run /setup first to configure the bot before using this command.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error resuming notifications: {str(e)}")
        logger.error(f"Error in resume command: {e}")
    finally:
        db.close()


# Callback Query Handler for inline keyboards

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "help":
        help_text = (
            "📖 <b>HackRadar Commands</b>\n\n"
            "<b>🔍 Search & Browse</b>\n"
            "/search [keyword] - Search hackathons\n"
            "/upcoming [days] - Hackathons starting soon\n"
            "/platform [name] - Filter by platform\n\n"
            "<b>🔔 Personal Alerts</b>\n"
            "/subscribe [theme] - Get DM alerts\n"
            "/unsubscribe [theme] - Stop DM alerts\n"
            "/subscriptions - View subscriptions\n\n"
            "<b>🔧 Group Setup (Admin Only)</b>\n"
            "/setup - Configure preferences\n"
            "/pause - Pause notifications\n"
            "/resume - Resume notifications"
        )
        await query.edit_message_text(help_text, parse_mode=ParseMode.HTML)
    
    elif data == "setup_platforms":
        keyboard = [
            [InlineKeyboardButton("✅ Devfolio" if "devfolio" in context.chat_data.get('setup_platforms', []) else "Devfolio", 
                                callback_data="toggle_platform_devfolio")],
            [InlineKeyboardButton("✅ Devpost" if "devpost" in context.chat_data.get('setup_platforms', []) else "Devpost", 
                                callback_data="toggle_platform_devpost")],
            [InlineKeyboardButton("✅ Unstop" if "unstop" in context.chat_data.get('setup_platforms', []) else "Unstop", 
                                callback_data="toggle_platform_unstop")],
            [InlineKeyboardButton("✅ DoraHacks" if "dorahacks" in context.chat_data.get('setup_platforms', []) else "DoraHacks", 
                                callback_data="toggle_platform_dorahacks")],
            [InlineKeyboardButton("✅ Hack2Skill" if "hack2skill" in context.chat_data.get('setup_platforms', []) else "Hack2Skill", 
                                callback_data="toggle_platform_hack2skill")],
            [InlineKeyboardButton("✅ Kaggle" if "kaggle" in context.chat_data.get('setup_platforms', []) else "Kaggle", 
                                callback_data="toggle_platform_kaggle")],
            [InlineKeyboardButton("✅ MLH" if "mlh" in context.chat_data.get('setup_platforms', []) else "MLH", 
                                callback_data="toggle_platform_mlh")],
            [InlineKeyboardButton("« Back", callback_data="setup_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📱 <b>Select Platforms</b>\n\nTap to toggle platforms:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data.startswith("toggle_platform_"):
        platform = data.replace("toggle_platform_", "")
        platforms = context.chat_data.get('setup_platforms', [])
        
        if platform in platforms:
            platforms.remove(platform)
        else:
            platforms.append(platform)
        
        context.chat_data['setup_platforms'] = platforms
        
        # Refresh the platform selection menu
        keyboard = [
            [InlineKeyboardButton("✅ Devfolio" if "devfolio" in platforms else "Devfolio", 
                                callback_data="toggle_platform_devfolio")],
            [InlineKeyboardButton("✅ Devpost" if "devpost" in platforms else "Devpost", 
                                callback_data="toggle_platform_devpost")],
            [InlineKeyboardButton("✅ Unstop" if "unstop" in platforms else "Unstop", 
                                callback_data="toggle_platform_unstop")],
            [InlineKeyboardButton("✅ DoraHacks" if "dorahacks" in platforms else "DoraHacks", 
                                callback_data="toggle_platform_dorahacks")],
            [InlineKeyboardButton("✅ Hack2Skill" if "hack2skill" in platforms else "Hack2Skill", 
                                callback_data="toggle_platform_hack2skill")],
            [InlineKeyboardButton("✅ Kaggle" if "kaggle" in platforms else "Kaggle", 
                                callback_data="toggle_platform_kaggle")],
            [InlineKeyboardButton("✅ MLH" if "mlh" in platforms else "MLH", 
                                callback_data="toggle_platform_mlh")],
            [InlineKeyboardButton("« Back", callback_data="setup_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    elif data == "setup_themes":
        keyboard = [
            [InlineKeyboardButton("✅ AI/ML" if "ai" in context.chat_data.get('setup_themes', []) else "AI/ML", 
                                callback_data="toggle_theme_ai")],
            [InlineKeyboardButton("✅ Blockchain/Web3" if "blockchain" in context.chat_data.get('setup_themes', []) else "Blockchain/Web3", 
                                callback_data="toggle_theme_blockchain")],
            [InlineKeyboardButton("✅ Web Development" if "web" in context.chat_data.get('setup_themes', []) else "Web Development", 
                                callback_data="toggle_theme_web")],
            [InlineKeyboardButton("✅ Mobile App" if "mobile" in context.chat_data.get('setup_themes', []) else "Mobile App", 
                                callback_data="toggle_theme_mobile")],
            [InlineKeyboardButton("✅ Data Science" if "data" in context.chat_data.get('setup_themes', []) else "Data Science", 
                                callback_data="toggle_theme_data")],
            [InlineKeyboardButton("✅ IoT" if "iot" in context.chat_data.get('setup_themes', []) else "IoT", 
                                callback_data="toggle_theme_iot")],
            [InlineKeyboardButton("✅ Cloud" if "cloud" in context.chat_data.get('setup_themes', []) else "Cloud", 
                                callback_data="toggle_theme_cloud")],
            [InlineKeyboardButton("✅ Cybersecurity" if "security" in context.chat_data.get('setup_themes', []) else "Cybersecurity", 
                                callback_data="toggle_theme_security")],
            [InlineKeyboardButton("« Back", callback_data="setup_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎯 <b>Select Themes</b>\n\nTap to toggle themes:",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data.startswith("toggle_theme_"):
        theme = data.replace("toggle_theme_", "")
        themes = context.chat_data.get('setup_themes', [])
        
        if theme in themes:
            themes.remove(theme)
        else:
            themes.append(theme)
        
        context.chat_data['setup_themes'] = themes
        
        # Refresh the theme selection menu
        keyboard = [
            [InlineKeyboardButton("✅ AI/ML" if "ai" in themes else "AI/ML", 
                                callback_data="toggle_theme_ai")],
            [InlineKeyboardButton("✅ Blockchain/Web3" if "blockchain" in themes else "Blockchain/Web3", 
                                callback_data="toggle_theme_blockchain")],
            [InlineKeyboardButton("✅ Web Development" if "web" in themes else "Web Development", 
                                callback_data="toggle_theme_web")],
            [InlineKeyboardButton("✅ Mobile App" if "mobile" in themes else "Mobile App", 
                                callback_data="toggle_theme_mobile")],
            [InlineKeyboardButton("✅ Data Science" if "data" in themes else "Data Science", 
                                callback_data="toggle_theme_data")],
            [InlineKeyboardButton("✅ IoT" if "iot" in themes else "IoT", 
                                callback_data="toggle_theme_iot")],
            [InlineKeyboardButton("✅ Cloud" if "cloud" in themes else "Cloud", 
                                callback_data="toggle_theme_cloud")],
            [InlineKeyboardButton("✅ Cybersecurity" if "security" in themes else "Cybersecurity", 
                                callback_data="toggle_theme_security")],
            [InlineKeyboardButton("« Back", callback_data="setup_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    elif data == "setup_back":
        setup_text = (
            "⚙️ <b>HackRadar Setup</b>\n\n"
            "Please configure your preferences:\n\n"
            "1. Select platforms to track\n"
            "2. Select themes to track\n"
            "3. Confirm your selection\n\n"
            "💡 <i>Leave selections empty to receive all notifications.</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("📱 Select Platforms", callback_data="setup_platforms")],
            [InlineKeyboardButton("🎯 Select Themes", callback_data="setup_themes")],
            [InlineKeyboardButton("✅ Save Preferences", callback_data="setup_save")],
            [InlineKeyboardButton("❌ Cancel", callback_data="setup_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            setup_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    elif data == "setup_save":
        platforms = context.chat_data.get('setup_platforms', [])
        themes = context.chat_data.get('setup_themes', [])
        chat_id = str(update.effective_chat.id)
        
        db = SessionLocal()
        try:
            update_guild_preferences(db, chat_id, chat_id, platforms, themes)
            
            success_text = (
                "✅ <b>Setup Complete!</b>\n\n"
                "Your preferences have been saved successfully!\n\n"
                f"<b>Platforms:</b> {', '.join(platforms) if platforms else 'All (Default)'}\n"
                f"<b>Themes:</b> {', '.join(themes) if themes else 'All (Default)'}\n\n"
                "🎉 You'll start receiving hackathon notifications soon."
            )
            
            keyboard = [
                [InlineKeyboardButton("⭐ Star on GitHub", url="https://github.com/Spartan-71/Telegram-Hackathon-Bot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                success_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
            # Clear setup state
            context.chat_data.clear()
        except Exception as e:
            await query.edit_message_text(f"❌ Error saving preferences: {str(e)}")
            logger.error(f"Error in setup save: {e}")
        finally:
            db.close()
    
    elif data == "setup_cancel":
        await query.edit_message_text("❌ Setup cancelled.")
        context.chat_data.clear()


# Background task

async def check_and_notify_hackathons(application):
    """Background task that fetches hackathons and sends notifications."""
    try:
        logger.info("Starting hackathon fetch and notification check")
        new_hackathons = fetch_and_store_hackathons()
        
        if not new_hackathons:
            logger.info("No new hackathons found")
            return
        
        logger.info(f"Found {len(new_hackathons)} new hackathons, sending notifications")
        
        # Send notifications to all groups
        await send_hackathon_notifications(application, new_hackathons)
        
        # Notify subscribers via DM
        await notify_subscribers(application, new_hackathons)
        
        logger.info("Completed hackathon notifications")
    except Exception as e:
        logger.error(f"Error in check_and_notify_hackathons task: {e}")


async def post_init(application: Application) -> None:
    """Initialize scheduler after application starts."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_notify_hackathons,
        'interval',
        hours=12,
        args=[application]
    )
    scheduler.start()
    logger.info("Background scheduler started")


async def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN is not set in the environment")
    
    # Create application
    application = Application.builder().token(token).post_init(post_init).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("platform", platform_command))
    application.add_handler(CommandHandler("upcoming", upcoming_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("subscriptions", subscriptions_command))
    application.add_handler(CommandHandler("setup", setup_command))
    application.add_handler(CommandHandler("pause", pause_command))
    application.add_handler(CommandHandler("resume", resume_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Initialize and start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Bot started successfully!")
    
    # Keep the process alive
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
