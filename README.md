# Daily News Agent — AI-Powered News Briefing

An automated Python application that collects news from RSS feeds, generates concise AI-powered summaries using NVIDIA Nemotron, and delivers a daily briefing through Telegram and Gmail.

## Overview

Daily News Agent reduces the time spent browsing multiple news sources by collecting headlines from four categories and summarizing selected stories in simple English.

The application fetches RSS headlines and descriptions, sends up to eight selected stories to an LLM for summarization, and delivers the resulting briefing through Telegram and email.

## Features

- **Automated news collection:** Fetches news from Google News RSS feeds.
- **Four news categories:** India, AI and technology, world news, and cricket and sports.
- **AI-powered summarization:** Uses NVIDIA Nemotron through an OpenAI-compatible API.
- **Concise summaries:** Produces three to five bullet points when the available information supports them.
- **Dual-channel delivery:** Sends briefings to Telegram and Gmail.
- **Original source links:** Includes links to the original news items.
- **Fallback handling:** Uses the original headline and link when AI summarization fails.
- **Scheduled execution:** Uses GitHub Actions and cron-job.org to automate execution.
- **Duplicate filtering:** Removes duplicate headlines within a single briefing run.

## Technology Stack

- **Language:** Python 3.12
- **AI model:** NVIDIA Nemotron 3.5 Super VL 120B A12B
- **News source:** Google News RSS
- **AI integration:** OpenAI Python SDK with NVIDIA's compatible API
- **Automation:** GitHub Actions and cron-job.org
- **Notifications:** Telegram Bot API and Gmail SMTP
- **Version control:** Git and GitHub

## Architecture

1. cron-job.org triggers the GitHub Actions workflow.
2. GitHub Actions checks out the repository and prepares the Python environment.
3. The Python application fetches RSS feeds and extracts headlines, descriptions, and links.
4. Selected stories are sent to NVIDIA Nemotron for summarization.
5. The application formats the briefing and sends it to Telegram and Gmail.

## Project Structure

```text
daily-news-agent/
├── .github/
│   └── workflows/
│       └── daily-news.yml
├── news_agent.py
└── README.md
```

## Setup and Configuration

### Prerequisites

- Python 3.12 or compatible environment
- A GitHub account
- A Telegram bot and chat ID
- A Gmail account with an app password
- An NVIDIA API key with access to the selected model

### Install dependencies

```bash
pip install openai
```

### Configure environment variables

The application uses the following environment variables:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Authenticates the Telegram bot |
| `TELEGRAM_CHAT_ID` | Identifies the destination chat |
| `GMAIL_ADDRESS` | Gmail sender and recipient address |
| `GMAIL_APP_PASSWORD` | Authenticates Gmail SMTP |
| `NVIDIA_API_KEY` | Authenticates NVIDIA model requests |

For automated execution, add these values under your repository's **Settings → Secrets and variables → Actions**.

Never commit API keys, passwords, or bot tokens to the repository.

### Run locally

After configuring the required environment variables, run:

```bash
python news_agent.py
```

### Automated execution

The GitHub Actions workflow can be triggered manually. cron-job.org is configured to send a scheduled workflow-dispatch request to GitHub.

The intended production schedule is 7:00 AM India Standard Time (IST). Scheduled execution should be verified through cron-job.org history and GitHub Actions run logs.

## Error Handling and Limitations

- If an individual AI summary fails, the application falls back to the original headline and link.
- If a news feed fails, the application records the feed failure and continues processing the remaining categories.
- If every news feed fails, the application stops instead of sending an empty briefing.
- AI summaries are based on RSS headlines and descriptions; the application does not fetch or analyze full article text.
- Duplicate filtering currently applies within one execution, not across different days.
- API availability, rate limits, and free-tier access depend on the provider's current terms.

## Future Improvements

- Persist previously sent story identifiers to avoid repeated stories across daily briefings.
- Improve news relevance ranking and cross-source deduplication.
- Add structured logging and clearer delivery failure reporting.
- Add automated tests for RSS parsing, summarization fallback, and message formatting.
- Improve monitoring of scheduled runs and notification delivery.

## Learning Outcomes

This project demonstrates practical experience with Python automation, RSS and HTTP requests, external LLM API integration, environment-based secret management, scheduled workflows, error handling, and messaging integrations.

## License

Choose and add an appropriate open-source license before distributing the project for reuse.
