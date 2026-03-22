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
Ayudas a distribuir ingresos en metas de ahorro usando cUSD en Celo.

Cuando el usuario diga que recibio dinero -> muestra el plan de distribucion.
Cuando confirme -> ejecuta el plan.
Cuando diga mis metas -> muestra sus metas actuales.
Siempre termina los planes con: Lo ejecuto? Responde SI para confirmar."""

_goals   = {}
_plans   = {}
_history = {}

def _get_goals(uid):    return _goals.get(uid, list(DEMO_GOALS))
def _get_hist(uid):     return _history.get(uid, [])
def _save_hist(uid, h): _history[uid] = h[-20:]

def _amount(text):
    for p in [r'\$\s*([\d,]+(?:\.\d{1,2})?)',
              r'([\d,]+)\s*(?:dolares?|usd|soles?|cusd)',
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

def _execute(uid):
    plan = _plans.pop(uid, None)
    if not plan:
        return "No hay plan pendiente. Dime cuanto recibiste."
    lines = ["[OK] Distribuido!\n"]
    for it in plan.items:
        h = f"0xSIM{it.goal_id[:4].upper()}{int(it.amount*100):05d}"
        lines.append(f"  - {it.goal_name}: ${it.amount:.2f} cUSD")
        lines.append(f"    Ver: https://alfajores.celoscan.io/tx/{h}")
    if plan.unallocated > 0.01:
        lines.append(f"\n  Sin asignar: ${plan.unallocated:.2f}")
    lines.append("\nNOTA: Txs reales en Celo disponibles en Fase 2")
    return "\n".join(lines)

def _show_goals(uid):
    goals = _get_goals(uid)
    if not goals: return "No tienes metas activas."
    lines = ["Tus metas de ahorro:\n"]
    for g in goals:
        pct = g.current/g.target*100 if g.target else 0
        done = int(pct/10)
        bar  = "#"*done + "-"*(10-done)
        lines.append(
            f"{g.name}\n"
            f"  [{bar}] {pct:.0f}%\n"
            f"  ${g.current:.0f} / ${g.target:.0f} cUSD"
        )
    return "\n\n".join(lines)

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
            reply = _execute(uid)
            _save_hist(uid, hist + [HumanMessage(content=message),
                                    AIMessage(content=reply)])
            return reply

        # Ingreso detectado
        amt = _amount(message)
        if amt and amt > 0:
            plan = calculate_distribution(amt, _get_goals(uid))
            _plans[uid] = plan
            reply = plan.summary + "\n\nLo ejecuto? Responde SI para confirmar."
            _save_hist(uid, hist + [HumanMessage(content=message),
                                    AIMessage(content=reply)])
            return reply

        # Ver metas
        if _is_goals(message):
            reply = _show_goals(uid)
            _save_hist(uid, hist + [HumanMessage(content=message),
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

        _save_hist(uid, hist + [HumanMessage(content=message),
                                AIMessage(content=reply)])
        return reply


_inst = None

def get_agent():
    global _inst
    if _inst is None:
        _inst = SaverAgent()
    return _inst


if __name__ == "__main__":
    print("=== Test SaverAgent ===\n")
    a = SaverAgent()
    uid = "test"
    tests = [
        "Hola",
        "Recibi $300",
        "si",
        "mis metas",
    ]
    for msg in tests:
        print(f"Usuario: {msg}")
        print(f"SaverAgent: {a.chat(uid, msg)}")
        print("-" * 40)
