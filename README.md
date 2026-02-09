<img alt="Minimal Illustration Music SoundCloud Banner" src="https://github.com/user-attachments/assets/810ca1a2-d314-4ca6-8c6b-7c641c183097" />

## What is it?

HackRadar is a **Telegram Bot** that tracks upcoming hackathons from **7 major platforms**: **MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill**. It fetches data periodically and provides two bot types: an **interactive bot** for user commands and subscriptions, and a **channel bot** for automated broadcasting.

### 🌟 Key Highlights
- 🤖 **Fully Automated**: Fetches and notifies every 12 hours without manual intervention
- 🌐 **7 Platform Coverage**: Aggregates hackathons from MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill
- 💬 **Two Bot Types**: Interactive bot for users + Channel bot for broadcasting
- 🎯 **Dual-Level Filtering**: Group-wide preferences + individual user subscriptions with DM alerts
- ⚡ **Interactive Setup**: Rich UI with inline keyboards and buttons for easy configuration
- 🔍 **Powerful Search**: Search, filter by platform, and browse upcoming events on-demand

## 🚀 Features

### Interactive Bot (`telegram-bot.py`)
*   **User Commands**: Search, filter, and browse hackathons with `/search`, `/platform`, `/upcoming`
*   **Personalized Subscriptions**: Subscribe to specific themes and receive DM alerts for matching hackathons
*   **Group Setup**: Configure group preferences with interactive inline keyboards
*   **Smart Filtering**: Filter by platforms and themes to receive only relevant updates
*   **Pause/Resume Controls**: Administrators can pause and resume group notifications

### Channel Bot (`telegram-channel-bot.py`)
*   **Automated Broadcasting**: Posts ALL new hackathons to a Telegram channel automatically
*   **No Setup Required**: Just add bot to channel and it starts posting
*   **Rich Formatting**: Beautiful messages with event banners, prizes, and registration links
*   **Scheduled Updates**: Runs every 6 hours (configurable)

### Platform Support
*   **Multi-Platform Scraping**: Supports **7 major platforms** - MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill
*   **Database**: Uses PostgreSQL to store hackathon data, group configurations, and user subscriptions
*   **Dockerized**: Easy deployment with Docker Compose

## 🤖 Interactive Bot Commands

### 🔧 Admin Commands (Groups Only)
| Command | Description |
| :--- | :--- |
| `/setup` | Configure group preferences (platforms, themes). Uses interactive inline keyboards. |
| `/pause` | Pause automatic hackathon notifications for the group. |
| `/resume` | Resume automatic hackathon notifications for the group. |

### 🔍 Discovery Commands
| Command | Description |
| :--- | :--- |
| `/search [keyword]` | Search for hackathons by keyword (searches titles, tags, and descriptions). |
| `/platform [name] [count]` | Get the latest hackathons from a specific platform. |
| `/upcoming [days]` | List hackathons starting in the next X days. |

### 🔔 Personal Subscription Commands
| Command | Description |
| :--- | :--- |
| `/subscribe [theme]` | Subscribe to DM notifications for a specific theme. Get alerted when matching hackathons are posted. |
| `/unsubscribe [theme]` | Unsubscribe from a theme's DM notifications. |
| `/subscriptions` | View all your active subscriptions. |

### ℹ️ Information Commands
| Command | Description |
| :--- | :--- |
| `/start` | Welcome message with quick action buttons. |
| `/help` | View the full command guide with all available commands and usage examples. |
| `/about` | Learn about HackRadar, view platform statistics, and access support links. |

---

## 📢 Channel Bot (Automated Broadcasting)

The channel bot automatically posts ALL new hackathons to a Telegram channel without any user interaction.

### Features
- ✅ Posts all hackathons automatically every 12 hours
- ✅ No commands or setup needed (just add to channel)
- ✅ Rich formatting with images and links
- ✅ Perfect for public announcement channels


## 🎨 Notification Format

HackRadar sends visually rich notifications including:
*   **Title**: Event name with a random fun emoji (🎉, 🚀, 💡, 🔥, 💻, 🏆, etc.).
*   **Core Details**:
    *   Duration (Start Date - End Date)
    *   Location
    *   Mode (Online/In-person/Hybrid)
    *   Status
*   **Additional Information** (where available from platform APIs):
    *   💰 Prize Pool & Rewards
    *   👥 Team Size
    *   ✅ Eligibility Criteria
*   **Visuals**: Event banner image (when available)
*   **Interactive Buttons**:
    *   `🚀 Check Details`: Direct link to the official hackathon registration page
    *   `🔔 Set Reminder`: Personal reminder feature (Coming Soon)

## ⚡ Quick Start (Docker)

1.  **Configure Environment**:
    Copy the example environment file and fill in your details:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` with your Telegram bot tokens and database credentials.

2.  **Run with Docker Compose**:
    ```bash
    # Start both interactive and channel bots
    docker compose up -d

    # Or start only interactive bot
    docker compose up -d db telegram-bot

    # Or start only channel bot
    docker compose up -d db telegram-channel-bot
    ```

    The bot(s) will start automatically and begin fetching hackathons.


## 🛠 Local Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Spartan-71/Telegram-Hackathon-Bot.git
    cd Telegram-Hackathon-Bot
    ```

2.  **Install dependencies**:
    This project uses `uv` for dependency management.
    ```bash
    uv pip install -e .
    ```

3.  **Set up PostgreSQL**:
    Ensure PostgreSQL is running locally and create a database (e.g., `hackradar`).

4.  **Configure Environment**:
    Create a `.env` file with your database credentials and Telegram bot tokens.
    ```bash
    cp .env.example .env
    # Edit .env with your tokens
    ```

5.  **Initialize Database**:
    ```bash
    python -m backend.init_db
    ```

6.  **Run the Bot(s)**:
    ```bash
    # Interactive bot
    uv run python telegram-bot.py

    # Or channel bot
    uv run python telegram-channel-bot.py

    # Or both (in separate terminals)
    ```

## 🏗️ Architecture & How It Works

### Components Overview
HackRadar is built with a modular architecture consisting of several key components:

1. **Interactive Bot (`telegram-bot.py`)**:
   - Handles all user interactions using python-telegram-bot
   - Implements commands and inline keyboards for interactive setup
   - Manages background tasks using APScheduler (every 12 hours)
   - Sends notifications to configured groups and subscriber DMs
   - Supports filtering by platform and theme

2. **Channel Bot (`telegram-channel-bot.py`)**:
   - Automated broadcaster for Telegram channels
   - Posts ALL new hackathons without filtering
   - No user interaction - fully automated
   - Runs on same 6-hour schedule
   - Perfect for public announcement channels

3. **Platform Adapters (`adapters/`)**:
   - Each adapter is responsible for fetching data from a specific platform
   - Supported platforms:
     - **Devfolio** (`devfolio.py`): Uses GraphQL API
     - **Devpost** (`devpost.py`): Web scraping with BeautifulSoup
     - **Unstop** (`unstop.py`): REST API integration
     - **DoraHacks** (`dorahacks.py`): REST API integration
     - **MLH** (`mlh.py`): Uses MLH's public API
     - **Kaggle** (`kaggle.py`): Kaggle API for competitions
     - **Hack2Skill** (`hack2skill.py`): REST API integration
   - Normalizes data from different sources into a unified `Hackathon` schema

4. **Database Layer (`backend/`)**:
   - **Models** (`models.py`): SQLAlchemy ORM models for:
     - `HackathonDB`: Stores all hackathon data
     - `GuildConfig`: Stores group-specific preferences (chat ID, platforms, themes, pause state)
     - `UserSubscription`: Tracks user theme subscriptions for DM alerts
   - **CRUD Operations** (`crud.py`): Database query functions for searching, filtering, and managing data
   - **Schemas** (`schemas.py`): Pydantic models for data validation

5. **Fetch & Store Engine (`fetch_and_store.py`)**:
   - Orchestrates the data fetching process across all adapters
   - Detects new hackathons by comparing against existing database records
   - Returns only newly added events to trigger notifications

### Workflow

#### Interactive Bot Setup
1. Admin runs `/setup` command in a Telegram group
2. Bot presents interactive inline keyboard to select:
   - Platforms to track (default: all 7 platforms)
   - Themes to filter (AI, Blockchain, Web, Mobile, Data Science, IoT, Cloud, Security)
3. Preferences are stored in PostgreSQL `guild_configs` table (using chat_id)

#### Channel Bot Setup
1. Create a Telegram channel
2. Add channel bot as administrator
3. Configure `TELEGRAM_CHANNEL_ID` in environment
4. Bot automatically posts all new hackathons to the channel

#### Automatic Notifications (Every 12 Hours)
1. Background task triggers `fetch_and_store_hackathons()`
2. All adapters fetch latest data from their respective platforms
3. New hackathons are identified and stored in the database
4. **Interactive Bot**: For each configured group:
   - Check if notifications are paused (skip if paused)
   - Apply platform and theme filters based on group preferences
   - Send formatted messages to the configured group
5. **Channel Bot**: Posts all new hackathons to the configured channel
6. **User Subscriptions**:
   - Match new hackathons against subscribed themes
   - Send personalized DMs to subscribed users

#### On-Demand Commands (Interactive Bot)
- `/search`, `/platform`, `/upcoming`: Query the database and return filtered results
- `/subscribe`, `/unsubscribe`, `/subscriptions`: Manage user preferences
- `/pause`, `/resume`: Update the `notifications_paused` flag

### Data Filtering

**Group-Level Filtering** (Interactive Bot - configured via `/setup`):
- **Platform Filter**: Only show hackathons from selected platforms
- **Theme Filter**: Only show hackathons matching selected themes (tags)
- Default: "all" (no filtering)

**Channel Bot**:
- No filtering - posts ALL new hackathons
- Perfect for comprehensive news feeds

**User-Level Subscriptions** (Interactive Bot - via `/subscribe`):
- Users receive DMs when new hackathons match their subscribed themes
- Matching is done by checking if the subscribed theme is a substring of any hackathon tag
- Example: Subscribing to "AI" matches hackathons tagged with "AI", "Generative AI", "AI/ML", etc.

## 🤝 Contributing

Contributions are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.
