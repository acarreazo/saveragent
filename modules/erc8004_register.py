"""
modules/erc8004_register.py
Registra SaverAgent en ERC-8004 Identity Registry.

Soporta Celo Sepolia (testnet) y Celo Mainnet.
Por defecto usa Sepolia para ahorrar gas.
"""
import os
import logging
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Redes disponibles ─────────────────────────────────────────────────
NETWORKS = {
    "sepolia": {
        "rpc":      "https://forno.celo-sepolia.celo-testnet.org",
        "chainId":  11142220,
        "name":     "Celo Sepolia Testnet",
        "identity": "0x8004A818BFB912233c491871b3d84c89A494BD9e",
        "reputation": "0x8004B663056A597Dffe9eCcC1965A193B7388713",
        "explorer": "https://celo-sepolia.blockscout.com",
        "agentscan": "https://agentscan.io",
    },
    "mainnet": {
        "rpc":      "https://forno.celo.org",
        "chainId":  42220,
        "name":     "Celo Mainnet",
        "identity": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
        "reputation": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
        "explorer": "https://celoscan.io",
        "agentscan": "https://agentscan.io",
    }
}

# Usar Sepolia por defecto (mas barato, igual de valido para hackathon)
NETWORK = os.getenv("ERC8004_NETWORK", "sepolia")
NET     = NETWORKS[NETWORK]

PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY", "")

# URL publica del agent.json — raw GitHub
AGENT_URI = (
    "https://raw.githubusercontent.com/acarreazo/saveragent"
    "/main/agent.json"
)

# ABI minimo Identity Registry (ERC-721 + register)
IDENTITY_ABI = [
    {
        "name": "register",
        "type": "function",
        "inputs": [{"name": "agentURI", "type": "string"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable"
    },
    {
        "name": "totalSupply",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "ownerOf",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view"
    },
    {
        "name": "tokenURI",
        "type": "function",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view"
    },
    {
        "name": "Transfer",
        "type": "event",
        "inputs": [
            {"name": "from",    "type": "address", "indexed": True},
            {"name": "to",      "type": "address", "indexed": True},
            {"name": "tokenId", "type": "uint256", "indexed": True}
        ]
    }
]

# ABI minimo Reputation Registry
REPUTATION_ABI = [
    {
        "name": "giveFeedback",
        "type": "function",
        "inputs": [
            {"name": "agentId",      "type": "uint256"},
            {"name": "score",        "type": "uint256"},
            {"name": "decimals",     "type": "uint256"},
            {"name": "tag1",         "type": "string"},
            {"name": "tag2",         "type": "string"},
            {"name": "endpoint",     "type": "string"},
            {"name": "feedbackURI",  "type": "string"},
            {"name": "feedbackHash", "type": "bytes32"}
        ],
        "outputs": [],
        "stateMutability": "nonpayable"
    },
    {
        "name": "getSummary",
        "type": "function",
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "outputs": [
            {"name": "averageScore",  "type": "uint256"},
            {"name": "totalFeedback", "type": "uint256"}
        ],
        "stateMutability": "view"
    }
]


def connect() -> tuple:
    """Conecta a la red y retorna (w3, account, identity_contract)."""
    w3 = Web3(Web3.HTTPProvider(NET["rpc"]))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        raise ConnectionError(f"No se puede conectar a {NET['name']}")

    account = w3.eth.account.from_key(PRIVATE_KEY)

    identity = w3.eth.contract(
        address=Web3.to_checksum_address(NET["identity"]),
        abi=IDENTITY_ABI
    )
    return w3, account, identity


def register_agent() -> int | None:
    """Registra SaverAgent en ERC-8004 y retorna el agentId."""

    if not PRIVATE_KEY:
        print("ERROR: AGENT_PRIVATE_KEY no configurado en .env")
        return None

    print(f"Red: {NET['name']}")
    print(f"Identity Registry: {NET['identity']}")

    w3, account, identity = connect()

    print(f"Wallet: {account.address}")

    # Balance
    bal     = w3.eth.get_balance(account.address)
    bal_eth = float(w3.from_wei(bal, "ether"))
    print(f"Balance: {bal_eth:.4f} CELO")

    if bal_eth < 0.001:
        print("ERROR: Balance insuficiente. Necesitas al menos 0.001 CELO.")
        return None

    # Total agentes antes
    total = identity.functions.totalSupply().call()
    print(f"Agentes registrados en ERC-8004: {total}")
    print(f"\nRegistrando con URI: {AGENT_URI}")

    # Construir tx
    gas_price = w3.eth.gas_price * 2
    nonce     = w3.eth.get_transaction_count(account.address)

    tx = identity.functions.register(AGENT_URI).build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gas":      200_000,
        "gasPrice": gas_price,
        "chainId":  NET["chainId"],
    })

    # Firmar y enviar
    signed  = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex  = "0x" + tx_hash.hex() if not tx_hash.hex().startswith("0x") else tx_hash.hex()

    print(f"Tx enviada: {tx_hex}")
    print("Esperando confirmacion (30-60 seg)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.status == 1:
        # Leer eventos Transfer para obtener el tokenId
        agent_id = None
        try:
            logs = identity.events.Transfer().process_receipt(receipt)
            if logs:
                agent_id = logs[0]["args"]["tokenId"]
        except Exception:
            # Fallback: totalSupply despues del registro
            agent_id = identity.functions.totalSupply().call()

        print(f"\nREGISTRO EXITOSO!")
        print(f"  agentId:  {agent_id}")
        print(f"  Tx:       {NET['explorer']}/tx/{tx_hex}")
        print(f"  agentscan: {NET['agentscan']}/agent/{NET['chainId']}/{agent_id}")
        print(f"\nGuarda este agentId en .env:")
        print(f"  ERC8004_AGENT_ID={agent_id}")
        print(f"\nUsa este agentId en el tweet de submit de Celo.")
        return agent_id
    else:
        print(f"ERROR: Tx fallida — {tx_hex}")
        return None


def give_feedback(agent_id: int, score: int = 90):
    """Envia feedback de reputacion al agente (llama el autonomous loop)."""
    if not PRIVATE_KEY:
        return

    w3, account, _ = connect()

    reputation = w3.eth.contract(
        address=Web3.to_checksum_address(NET["reputation"]),
        abi=REPUTATION_ABI
    )

    import hashlib
    feedback_text = f"SaverAgent executed distribution successfully. Score: {score}"
    feedback_hash = "0x" + hashlib.keccak_256(
        feedback_text.encode()
    ).hexdigest()

    gas_price = w3.eth.gas_price * 2
    nonce     = w3.eth.get_transaction_count(account.address)

    tx = reputation.functions.giveFeedback(
        agent_id,
        score,
        0,
        "starred",
        "successRate",
        "https://t.me/SaverAgentBot",
        "",
        bytes.fromhex(feedback_hash[2:])
    ).build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gas":      150_000,
        "gasPrice": gas_price,
        "chainId":  NET["chainId"],
    })

    signed  = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    log.info(f"Feedback enviado: 0x{tx_hash.hex()}")


if __name__ == "__main__":
    print("=== ERC-8004 Registration — SaverAgent ===\n")
    agent_id = register_agent()

    if agent_id:
        # Agregar al .env automaticamente
        env_path = ".env"
        with open(env_path, "a") as f:
            f.write(f"\nERC8004_AGENT_ID={agent_id}")
        print(f"\nagentId guardado en .env: ERC8004_AGENT_ID={agent_id}")
