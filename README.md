# SaverAgent

Autonomous AI savings agent built on Celo for LATAM families.

## What it does

SaverAgent distributes income automatically across savings goals using cUSD on Celo.
Users interact via Telegram in Spanish — no crypto knowledge required.

## Demo

Send "Recibi $300" to the bot ? get a distribution plan ? confirm ? real cUSD transactions on Celo.

## Tech Stack

- Python 3.12
- Telegram Bot (python-telegram-bot)
- Celo Alfajores — cUSD stablecoin transactions
- Solidity — SpendingLimit.sol (on-chain spending limits)
- ERC-8004 — agent identity and reputation
- web3.py — blockchain interaction

## Setup
```bash
git clone https://github.com/acarreazo/saveragent.git
cd saveragent
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python ui/telegram_bot.py
```

## Hackathon

Built for Celo Build Agents for the Real World Hackathon V2
