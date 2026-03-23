import os, re, logging
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.budget import calculate_distribution, DEMO_GOALS, DistributionPlan

load_dotenv()
log = logging.getLogger(__name__)

SYSTEM = """Eres SaverAgent, asistente financiero para familias latinoamericanas.
Hablas SIEMPRE en español. Eres directo, amable y claro.
Ayudas a distribuir ingresos en metas de ahorro usando stablecoins en Celo.

Cuando el usuario diga que recibio dinero -> muestra el plan de distribucion.
Cuando confirme -> ejecuta el plan con transacciones reales en Celo Sepolia.
Cuando diga mis metas -> muestra sus metas actuales.
Cuando diga balance o saldo -> muestra el balance de la wallet.
Siempre termina los planes con: Lo ejecuto? Responde SI para confirmar."""

_goals   = {}
_plans   = {}
_history = {}

def _get_goals(uid):    return _goals.get(uid, list(DEMO_GOALS))
def _get_hist(uid):     return _history.get(uid, [])
def _save_hist(uid, h): _history[uid] = h[-20:]

def _amount(text):
    for p in [r'\$\s*([\d,]+(?:\.\d{1,2})?)',
              r'([\d,]+)\s*(?:dolares?|usd|soles?|usdc)',
              r'(?:recibi|llegaron|cobre|gane)\s+([\d,]+)']:
        m = re.search(p, text.lower())
        if m:
            try: return float(m.group(1).replace(',',''))
            except: pass
    return None

def _confirm(text):
    return any(w in text.lower() for w in
               ['si','yes','ok','perfecto','ejecuta',
                'ejecutar','dale','adelante','hazlo','confirmo'])

def _is_goals(text):
    return any(w in text.lower() for w in
               ['mis metas','metas','objetivos','cuanto llevo'])

def _is_balance(text):
    return any(w in text.lower() for w in
               ['balance','saldo','cuanto tengo','mi wallet','wallet'])

def _execute_real(uid: str) -> str:
    plan = _plans.pop(uid, None)
    if not plan:
        return "No hay plan pendiente. Dime cuanto recibiste."

    try:
        from core.wallet import get_wallet
        wallet = get_wallet()

        balance  = wallet.get_cusd_balance()
        needed   = sum(item.amount for item in plan.items)

        # Para el demo usamos montos pequeños
        # Si el balance es menor al plan, ajustamos proporcionalmente
        if balance < needed and balance > 0:
            factor = balance * 0.9 / needed
            for item in plan.items:
                item.amount = round(item.amount * factor, 4)
            needed = sum(item.amount for item in plan.items)

        if balance < needed:
            return (
                f"Balance insuficiente en la wallet del agente.\n"
                f"Disponible: ${balance:.4f} USDC\n"
                f"Necesario:  ${needed:.4f} USDC\n\n"
                f"Recarga en: https://v2-app.mento.org"
            )

        results = wallet.execute_distribution(plan.items)

        lines = ["Distribuido en Celo Sepolia!\n"]
        all_ok = True
        for r in results:
            if r.get("success"):
                lines.append(f"  - {r['goal_name']}: ${r['amount']:.4f} USDC")
                lines.append(f"    Ver: {r['explorer']}")
            else:
                all_ok = False
                lines.append(f"  - {r.get('goal_name','?')}: ERROR")
                lines.append(f"    {r.get('error','')[:80]}")

        if plan.unallocated > 0.0001:
            lines.append(f"\nSin asignar: ${plan.unallocated:.4f} USDC")

        if all_ok:
            lines.append("\nTodas las transacciones confirmadas en Celo Sepolia.")
        return "\n".join(lines)

    except Exception as e:
        log.error(f"Error wallet: {e}")
        # Fallback simulado si la wallet no esta configurada
        lines = ["[SIMULADO - agrega AGENT_PRIVATE_KEY en .env para txs reales]\n"]
        for item in plan.items:
            h = f"0xSIM{item.goal_id[:4].upper()}{int(item.amount*10000):06d}"
            lines.append(f"  - {item.goal_name}: ${item.amount:.4f} USDC")
            lines.append(f"    Ver: {EXPLORER_URL}/tx/{h}")
        return "\n".join(lines)

EXPLORER_URL = "https://celo-sepolia.blockscout.com"

def _show_goals(uid):
    goals = _get_goals(uid)
    if not goals: return "No tienes metas activas."
    lines = ["Tus metas de ahorro:\n"]
    for g in goals:
        pct  = g.current/g.target*100 if g.target else 0
        done = int(pct/10)
        bar  = "#"*done + "-"*(10-done)
        lines.append(
            f"{g.name}\n"
            f"  [{bar}] {pct:.0f}%\n"
            f"  ${g.current:.0f} / ${g.target:.0f}"
        )
    return "\n\n".join(lines)

def _show_balance(uid):
    try:
        from core.wallet import get_wallet
        wallet = get_wallet()
        return wallet.status()
    except Exception as e:
        return f"No se pudo leer el balance: {e}"

class SaverAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            max_tokens=512,
        )

    def chat(self, uid: str, message: str) -> str:
        hist = _get_hist(uid)

        # Confirmar ejecucion
        if _confirm(message) and uid in _plans:
            reply = _execute_real(uid)
            _save_hist(uid, hist+[HumanMessage(content=message),
                                  AIMessage(content=reply)])
            return reply

        # Ingreso detectado
        amt = _amount(message)
        if amt and amt > 0:
            plan = calculate_distribution(amt, _get_goals(uid))
            _plans[uid] = plan
            reply = plan.summary + "\n\nLo ejecuto? Responde SI para confirmar."
            _save_hist(uid, hist+[HumanMessage(content=message),
                                  AIMessage(content=reply)])
            return reply

        # Ver metas
        if _is_goals(message):
            reply = _show_goals(uid)
            _save_hist(uid, hist+[HumanMessage(content=message),
                                  AIMessage(content=reply)])
            return reply

        # Ver balance
        if _is_balance(message):
            reply = _show_balance(uid)
            _save_hist(uid, hist+[HumanMessage(content=message),
                                  AIMessage(content=reply)])
            return reply

        # LLM general
        msgs = ([SystemMessage(content=SYSTEM)]
                + hist
                + [HumanMessage(content=message)])
        try:
            reply = self.llm.invoke(msgs).content
        except Exception as e:
            log.error(e)
            reply = "Tuve un problema tecnico. Dime cuanto recibiste. Ej: Recibi $300"

        _save_hist(uid, hist+[HumanMessage(content=message),
                               AIMessage(content=reply)])
        return reply


_inst = None

def get_agent():
    global _inst
    if _inst is None: _inst = SaverAgent()
    return _inst


if __name__ == "__main__":
    print("=== Test SaverAgent Milestone 2 ===\n")
    a   = SaverAgent()
    uid = "test"
    for msg in ["Hola", "Recibi $0.40", "si", "balance"]:
        print(f"Usuario: {msg}")
        print(f"SaverAgent: {a.chat(uid, msg)}")
        print("-"*40)
