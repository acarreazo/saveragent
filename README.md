# SaverAgent
 
Autonomous AI savings agent built on Celo for LATAM families.
 
> "Give every family the power to save automatically — so that income builds a future instead of disappearing into the present."
 
## What it does
 
SaverAgent distributes income automatically across savings goals using USDC on Celo Sepolia. Users interact via Telegram in Spanish — no crypto knowledge required.
 
**Example:**
```
User:       Recibi $300
SaverAgent: Plan para $300 USDC:
              - Fondo de emergencias: $150
              - Alquiler del mes: $90
              - Educacion hijos: $60
            Lo ejecuto? Responde SI para confirmar.
User:       si
SaverAgent: Distribuido en Celo Sepolia!
              - Fondo de emergencias: $150 USDC
                Ver: https://celo-sepolia.blockscout.com/tx/0x...
              - Alquiler del mes: $90 USDC
                Ver: https://celo-sepolia.blockscout.com/tx/0x...
              - Educacion hijos: $60 USDC
                Ver: https://celo-sepolia.blockscout.com/tx/0x...
```
 
## Live Transactions on Celo Sepolia
 
Real USDC transactions confirmed on Celo Sepolia Testnet:
- https://celo-sepolia.blockscout.com/tx/0xe980da84fa00b63e3f901e5324aed724d138112555adad2270f2781ba41bf3a4
- https://celo-sepolia.blockscout.com/tx/0x551b6dd9770565af5f139543fb0466627168d8fd54664cdd84433b15025ff0f9
- https://celo-sepolia.blockscout.com/tx/0x7d23e5fc2592ceeb244f435c34a118644d812a08262938c0a1468450d1e75eea
 
## Architecture
 
3-agent system:
- **Agent 1 — Conversational Saver**: talks to the user in Spanish via Telegram
- **Agent 2 — Budget Planner**: calculates optimal distribution (50/30/20 rule)
- **Agent 3 — Wallet Executor**: signs and broadcasts real USDC transactions on Celo

## Tech Stack

- Python 3.12
- Telegram Bot (python-telegram-bot)
- Celo Alfajores — cUSD stablecoin transactions
- Solidity — SpendingLimit.sol (on-chain spending limits)
- ERC-8004 — agent identity and reputation
- web3.py — blockchain interaction

## Smart Contract
 
`SpendingLimit.sol` — enforces on-chain spending permissions. The agent can never transfer more than the user authorized.
 
Network: Celo Sepolia Testnet (chainId: 11142220)

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

## Progress
 
- [x] Milestone 1 — Conversational Agent + Telegram Bot
- [x] Milestone 2 — Real USDC Transactions on Celo Sepolia
- [ ] Milestone 3 — ERC-8004 Identity + agentscan
- [ ] Milestone 4 — Cloud Deployment + Dynamic Goals
- [ ] Milestone 5 — Hackathon Submission + Demo Video