<img alt="Minimal Illustration Music SoundCloud Banner" src="https://github.com/user-attachments/assets/810ca1a2-d314-4ca6-8c6b-7c641c183097" />

## What is it?

HackRadar is a **Telegram Bot** that tracks upcoming hackathons from **7 major platforms** (MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, Hack2Skill). It periodically fetches data and exposes two bots: an **interactive bot** for search, filters, and subscriptions, and a **channel bot** for automated broadcasts.

## Features

### Interactive Bot (`telegram-bot.py`)
*   **User Commands**: Search, filter, and browse hackathons with `/search`, `/platform`, `/upcoming`
*   **Personalized Subscriptions**: Subscribe to specific themes and receive DM alerts for matching hackathons
*   **Group Setup**: Configure group preferences with interactive inline keyboards
*   **Smart Filtering**: Filter by platforms and themes to receive only relevant updates
*   **Pause/Resume Controls**: Administrators can pause and resume group notifications

### Channel Bot (`telegram-channel-bot.py`)
*   **Automated Broadcasting**: Posts all new hackathons to a Telegram channel on a schedule
*   **No Setup Required**: Add the bot to a channel and it starts posting
*   **Rich Formatting**: Messages with event banners, prizes, and registration links

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
*   **Title**: Event name with a random fun emoji/
    *   Duration (Start Date - End Date)
    *   Location
    *   Mode (Online/In-person/Hybrid)
    *   Status
*   **Additional Information** (where available from platform APIs):
    *   Prize Pool & Rewards
    *   Team Size
    *   Eligibility Criteria
*   **Visuals**: Event banner image (when available)
*   **Interactive Buttons**:
    *   `View Details`: Direct link to the official hackathon registration page

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

## 🤝 Contributing

Contributions are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.
