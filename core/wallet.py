"""
core/wallet.py
Agente 3 - Wallet Executor
Gestiona la wallet del agente en Celo Sepolia Testnet.
Ejecuta transferencias reales de USDC.
"""
import os
import logging
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()
log = logging.getLogger(__name__)

# ── Configuracion Celo Sepolia ────────────────────────────────────────
CELO_RPC     = os.getenv("CELO_RPC_URL",
               "https://forno.celo-sepolia.celo-testnet.org")
PRIVATE_KEY  = os.getenv("AGENT_PRIVATE_KEY", "")
CHAIN_ID     = 11142220
EXPLORER_URL = "https://celo-sepolia.blockscout.com"

# USDC en Celo Sepolia
CUSD_ADDRESS = "0x01C5C0122039549AD1493B8220cABEdD739BC44E"

ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "recipient", "type": "address"},
            {"name": "amount",    "type": "uint256"}
        ],
        "outputs":         [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable"
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs":          [{"name": "account", "type": "address"}],
        "outputs":         [{"name": "", "type": "uint256"}],
        "stateMutability": "view"
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs":  [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view"
    }
]


class CeloWallet:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(CELO_RPC))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not PRIVATE_KEY:
            raise ValueError(
                "AGENT_PRIVATE_KEY no configurado en .env\n"
                "MetaMask -> Account Details -> Export Private Key"
            )

        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.address = self.account.address

        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(CUSD_ADDRESS),
            abi=ERC20_ABI
        )

        try:
            self.decimals = self.usdc.functions.decimals().call()
        except Exception:
            self.decimals = 6

        log.info(f"Wallet: {self.address} | Celo Sepolia | Decimales: {self.decimals}")

    def is_connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def get_celo_balance(self) -> float:
        try:
            bal = self.w3.eth.get_balance(self.address)
            return float(self.w3.from_wei(bal, "ether"))
        except Exception as e:
            log.error(f"Error balance CELO: {e}")
            return 0.0

    def get_cusd_balance(self) -> float:
        try:
            bal = self.usdc.functions.balanceOf(self.address).call()
            return bal / (10 ** self.decimals)
        except Exception as e:
            log.error(f"Error balance USDC: {e}")
            return 0.0

    def transfer_cusd(
        self,
        to_address: str,
        amount_usd: float,
        nonce: int = None
    ) -> dict:
        """
        Transfiere USDC a una direccion.
        nonce: si se pasa, usa ese nonce (para multiples txs en secuencia)
        """
        try:
            to_checksum = Web3.to_checksum_address(to_address)
            amount_raw  = int(amount_usd * (10 ** self.decimals))

            # Verificar balance
            balance_raw = self.usdc.functions.balanceOf(self.address).call()
            if balance_raw < amount_raw:
                balance_usd = balance_raw / (10 ** self.decimals)
                return {
                    "success": False,
                    "error": (
                        f"Balance insuficiente: "
                        f"${balance_usd:.4f} USDC disponible, "
                        f"se necesita ${amount_usd:.4f}"
                    )
                }

            # Nonce — usar el pasado o leer de la red
            if nonce is None:
                nonce = self.w3.eth.get_transaction_count(self.address)

            # Gas price dinamico de la red x2
            gas_price = self.w3.eth.gas_price * 2

            tx = self.usdc.functions.transfer(
                to_checksum,
                amount_raw
            ).build_transaction({
                "from":     self.address,
                "nonce":    nonce,
                "gas":      100_000,
                "gasPrice": gas_price,
                "chainId":  CHAIN_ID,
            })

            signed  = self.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hex  = tx_hash.hex()

            log.info(f"Tx enviada nonce={nonce}: {tx_hex}")

            return {
                "success":  True,
                "tx_hash":  tx_hex,
                "amount":   amount_usd,
                "to":       to_address,
                "explorer": f"{EXPLORER_URL}/tx/0x{tx_hex}"
            }

        except Exception as e:
            log.error(f"Error transfer_cusd nonce={nonce}: {e}")
            return {"success": False, "error": str(e)}

    def execute_distribution(self, items: list) -> list:
        """
        Ejecuta multiples transferencias con nonces incrementales.
        Evita el error 'nonce too low' al enviar txs en secuencia.
        """
        results  = []
        # Leer nonce inicial una sola vez
        base_nonce = self.w3.eth.get_transaction_count(self.address)

        for i, item in enumerate(items):
            log.info(
                f"[{i+1}/{len(items)}] Enviando "
                f"${item.amount:.4f} USDC -> {item.goal_name}"
            )
            result = self.transfer_cusd(
                to_address=item.wallet_address,
                amount_usd=item.amount,
                nonce=base_nonce + i     # nonce unico por tx
            )
            result["goal_name"] = item.goal_name
            results.append(result)

        return results

    def status(self) -> str:
        connected = self.is_connected()
        usdc_bal  = self.get_cusd_balance()
        celo_bal  = self.get_celo_balance()
        return (
            f"Wallet: {self.address[:6]}...{self.address[-4:]}\n"
            f"Red: Celo Sepolia Testnet\n"
            f"Conectado: {'Si' if connected else 'No'}\n"
            f"Balance USDC: ${usdc_bal:.4f}\n"
            f"Balance CELO: {celo_bal:.4f} (para gas)"
        )


_wallet_instance = None

def get_wallet() -> CeloWallet:
    global _wallet_instance
    if _wallet_instance is None:
        _wallet_instance = CeloWallet()
    return _wallet_instance


if __name__ == "__main__":
    print("=== Test CeloWallet — Celo Sepolia ===\n")
    try:
        wallet = CeloWallet()
        print(wallet.status())
        print("\nTest transferencia $0.01 USDC...")
        result = wallet.transfer_cusd(
            "0x0000000000000000000000000000000000000001",
            0.01
        )
        if result["success"]:
            print(f"TX exitosa: {result['explorer']}")
        else:
            print(f"Error: {result['error']}")
    except ValueError as e:
        print(f"Error configuracion: {e}")
    except Exception as e:
        print(f"Error: {e}")
