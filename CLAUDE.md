# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot for an online AI avatar service by Tatyana Solo. The bot handles user onboarding, automated marketing sequences, subscription sales, payment processing through GetCourse integration, and AI chat functionality via OpenAI Assistant API.

## Development Setup

### Running the Bot
```bash
python main.py
```

### Running the Webhook Server (for payment processing)
```bash
python webhook_server.py
```

### Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```

Required environment variables (create `.env` file):
- `BOT_TOKEN` - Telegram bot token
- `GETCOURSE_API_URL` - GetCourse API endpoint
- `GETCOURSE_API_KEY` - GetCourse API key
- `ADMIN_IDS` - Comma-separated admin user IDs
- `SUPPORT_USERNAME` - Support contact username (default: @zabotasolo)

### Key Dependencies
- `aiogram==3.7.0` - Telegram Bot API framework
- `openai==1.54.4` - OpenAI API client for AI chat functionality
- `flask==3.0.0` - Webhook server for payment processing
- `aiohttp==3.9.5` - Async HTTP client for GetCourse integration

## Architecture

### Core Components

**Bot Entry Point (`main.py`)**
- Initializes aiogram Bot and Dispatcher with HTML parse mode
- Registers all handler routers in specific order (ai_chat must be last)
- Starts multiple background tasks: auto-spam and kupi-video delivery
- Comprehensive system checks on startup (token, directories, database)
- Graceful shutdown handling with task cancellation

**Handler Structure (`handlers/`)**
- `start.py` - Welcome messages, UTM tracking, video delivery, referral link processing
- `info.py` - Information pages (avatar description, features)
- `tariffs.py` - Subscription plans and pricing with referral discounts
- `support.py` - Customer support interface
- `payment.py` - Payment success handling and document delivery
- `subscription.py` - Manual subscription management for admins
- `referral.py` - Referral system with email registration and GetCourse integration
- `ai_chat.py` - OpenAI Assistant API integration with voice message support

**AI Integration (`openai_client.py`)**
- OpenAI Assistant API client with thread management
- Automatic rate limit handling and thread cleanup
- Voice message transcription via Whisper API
- HTML tag cleanup from AI responses
- Access control based on subscription status and admin permissions
- Automatic thread reset for critical rate limit errors

**Database Layer (`database.py`)**
- SQLite database with multiple tables: auto_spam_history, user_utm, user_subscriptions, openai_threads, referral_users, referral_bonuses
- Tracks spam completion status, UTM attribution, subscription status, and AI thread states
- Referral system with bonus tracking and email integration
- Thread management for OpenAI conversations

**Auto-Spam System (`auto_spam.py`)**
- Background task sending timed marketing messages
- 5-stage sequence: "2 super novosti" (1hr) → avatar info (2hr) → features (3hr) → reviews (4hr) → pricing (5hr)
- Reads content from `media/video/2_super_novosti.txt` and sends video circles
- User activity tracking to disable spam on interaction
- Hourly progression instead of minute-based

**Referral System (`handlers/referral.py`, `referral_getcourse.py`)**
- Email-based registration for referral participants
- Generates referral links: `https://t.me/bot?start=r{user_id}`
- Automatic bonus calculation and GetCourse webhook integration
- Access restricted to PERMANENT_ACCESS_IDS users only
- Dynamic pricing with referral balance discounts

**UTM Management (`utm_manager.py`)**
- Parses UTM parameters from `/start welcome2025_` links
- Caches UTM data in memory and persists to database
- Builds payment URLs with user attribution
- Tracks video delivery to prevent duplicates

**Payment Processing (`webhook_server.py`)**
- Flask webhook server for GetCourse payment notifications
- Extracts user IDs from payment metadata
- Sends success/failure notifications to users and admins
- Handles payment status validation and referral bonus distribution

**Background Tasks**
- `kupi_video.py` - Automated delivery of purchase-related videos based on schedule
- `thread_cleaner.py` - Periodic cleanup of old OpenAI threads for inactive users

### Key Design Patterns

**Access Control System:**
- `PERMANENT_ACCESS_IDS` in config.py for admin/referral access
- Subscription-based AI access with date restrictions
- Automatic access validation in AI chat handlers

**Two-Activity-Update System:**
- `update_user_activity()` - Permanently disables auto-spam on any bot interaction
- `update_user_activity_start_only()` - Updates activity for `/start` without disabling spam

**Payment ID Format:**
- `bot_{user_id}_{tariff}_{timestamp}` for tracking payments to specific users

**Referral Link Format:**
- `/start r{user_id}` for referral attribution

**UTM Parameter Format:**  
- `/start welcome2025_utm_source-ig_utm_medium-stories_utm_campaign-avatarai`

**Media File Handling:**
- Video files checked for 50MB limit before sending as video notes
- Image existence verified before sending with fallback to text-only
- Document attachments for legal compliance
- Video circles from `media/video/` directory for marketing content

**Error Handling:**
- HTML tag cleanup for OpenAI responses to prevent Telegram parsing errors
- Rate limit detection and automatic thread cleanup
- Graceful fallbacks for missing media files
- Comprehensive logging with configurable levels

## Configuration

**Pricing (`config.py`):**
- TARIFF_BASIC_PRICE = 5555 rubles
- TARIFF_VIP_PRICE = 7777 rubles
- REFERRAL_BONUS = 500 rubles per referral

**Access Control:**
- PERMANENT_ACCESS_IDS list for admin users and referral system access
- OpenAI access date restriction: July 30, 2025 15:00 MSK

**Media Paths:**
- Images: `media/images/`
- Videos: `media/videos/` (includes kupi videos and 2_super_novosti content)
- Documents: `media/documents/`
- Reviews: `media/otziv/` (10 review images)

**Text Content:**
All user-facing messages stored in `TEXTS` dictionary in `config.py`

## Important Implementation Notes

- Auto-spam now runs hourly progression instead of minute-based
- AI chat handler must be registered last to catch all unhandled messages
- OpenAI threads are automatically cleaned up to prevent rate limit accumulation
- Referral system requires email validation and GetCourse webhook integration
- Voice messages are transcribed via Whisper API before processing
- HTML responses from OpenAI are cleaned before sending to Telegram
- Payment webhooks trigger referral bonus distribution automatically
- System performs comprehensive startup checks before launching
- Background tasks are properly cancelled during shutdown