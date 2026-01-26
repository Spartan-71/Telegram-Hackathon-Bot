import os
import logging
import asyncio
from datetime import datetime

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from fetch_and_store import run as fetch_and_store_hackathons
import backend.models
from backend.models import HackathonDB
from backend.db import SessionLocal

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def format_hackathon_message(hackathon):
    """Format a hackathon as a Telegram message with HTML formatting."""
    emojis = ["🎉", "🚀", "💡", "🔥", "💻", "🏆", "🌟", "⚡", "🔮", "🛠️"]
    import random
    random_emoji = random.choice(emojis)
    
    text = f"{random_emoji} <b>{hackathon.title}</b>\n\n"
    text += f"<b>Duration:</b> {hackathon.start_date.strftime('%B %d')} - {hackathon.end_date.strftime('%B %d, %Y')}\n"
    text += f"<b>Location:</b> {hackathon.location}\n"
    text += f"<b>Mode:</b> {hackathon.mode}\n"
    text += f"<b>Status:</b> {hackathon.status}\n"
    text += f"<b>Platform:</b> {hackathon.source}\n\n"
    
    if hackathon.prize_pool:
        text += f"<b>Prizes:</b>\n{hackathon.prize_pool}\n\n"
    if hackathon.team_size:
        text += f"<b>Team Size:</b> {hackathon.team_size}\n"
    if hackathon.eligibility:
        text += f"<b>Eligibility:</b> {hackathon.eligibility}\n"
    
    return text, hackathon.banner_url, hackathon.url


async def send_to_channel(bot: Bot, channel_id: str, new_hackathons):
    """Send new hackathons to the specified Telegram channel."""
    if not new_hackathons:
        logger.info("No new hackathons to post")
        return
    
    success_count = 0
    error_count = 0
    
    for hackathon in new_hackathons:
        try:
            text, photo_url, hackathon_url = format_hackathon_message(hackathon)
            
            # Create inline keyboard with Register Now button
            keyboard = None
            if hackathon_url:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("View Details", url=hackathon_url)]
                ])
            
            if photo_url:
                # Send photo with caption
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
            else:
                # Send text message
                await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                    reply_markup=keyboard
                )
            
            success_count += 1
            logger.info(f"Posted hackathon '{hackathon.title}' to channel {channel_id}")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
            
        except TelegramError as e:
            error_count += 1
            logger.error(f"Failed to post hackathon '{hackathon.title}' to channel: {e}")
        except Exception as e:
            error_count += 1
            logger.error(f"Unexpected error posting hackathon '{hackathon.title}': {e}")
    
    logger.info(f"Channel posting complete: {success_count} successful, {error_count} failed")


async def check_and_post_hackathons(bot: Bot, channel_id: str):
    """Background task that fetches hackathons and posts to channel."""
    try:
        logger.info("Starting hackathon fetch and channel posting")
        new_hackathons = fetch_and_store_hackathons()
        
        if not new_hackathons:
            logger.info("No new hackathons found")
            return
        
        logger.info(f"Found {len(new_hackathons)} new hackathons, posting to channel")
        await send_to_channel(bot, channel_id, new_hackathons)
        
        logger.info("Completed channel posting")
        
    except Exception as e:
        logger.error(f"Error in check_and_post_hackathons task: {e}")


async def main():
    """Main function to run the channel bot."""
    # Get configuration from environment
    token = os.getenv("TELEGRAM_CHANNEL_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    
    if not token:
        raise RuntimeError("TELEGRAM_CHANNEL_BOT_TOKEN is not set in the environment")
    
    if not channel_id:
        raise RuntimeError("TELEGRAM_CHANNEL_ID is not set in the environment")
    
    # Validate channel_id format
    if not channel_id.startswith('@') and not channel_id.startswith('-'):
        logger.warning(
            f"Channel ID '{channel_id}' may be invalid. "
            "It should start with '@' (for public channels) or '-' (for private channels/groups)"
        )
    
    logger.info(f"Starting Telegram Channel Bot for channel: {channel_id}")
    
    # Create bot instance
    bot = Bot(token=token)
    
    # Verify bot can access the channel
    try:
        chat = await bot.get_chat(channel_id)
        logger.info(f"✅ Successfully connected to channel: {chat.title}")
    except TelegramError as e:
        logger.error(f"❌ Failed to access channel {channel_id}: {e}")
        logger.error("Make sure the bot is added as an administrator to the channel!")
        return
    
    # Set up scheduler for background tasks
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_post_hackathons,
        'interval',
        hours=6,
        args=[bot, channel_id]
    )
    scheduler.start()
    logger.info("Background scheduler started (runs every 6 hours)")
    
    # Run initial fetch and post
    logger.info("Running initial hackathon fetch and post...")
    await check_and_post_hackathons(bot, channel_id)
    
    # Keep the script running
    logger.info("Channel bot is now running. Press Ctrl+C to stop.")
    try:
        # Keep alive
        while True:
            await asyncio.sleep(7200)  # Sleep for 2 hour
    except KeyboardInterrupt:
        logger.info("Shutting down channel bot...")
        scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
