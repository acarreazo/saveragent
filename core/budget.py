from dataclasses import dataclass

@dataclass
class Goal:
    id: str
    name: str
    target: float
    current: float
    priority: int
    wallet_address: str

@dataclass
class DistributionItem:
    goal_id: str
    goal_name: str
    amount: float
    wallet_address: str
    reason: str

@dataclass
class DistributionPlan:
    total_income: float
    items: list
    unallocated: float
    summary: str

DEMO_GOALS = [
    Goal("emergencias", "Fondo de emergencias", 500.0,  80.0, 1,
         "0x0000000000000000000000000000000000000001"),
    Goal("alquiler",    "Alquiler del mes",     300.0,   0.0, 1,
         "0x0000000000000000000000000000000000000002"),
    Goal("educacion",   "Educacion hijos",      200.0,  50.0, 2,
         "0x0000000000000000000000000000000000000003"),
]

def calculate_distribution(income: float, goals: list) -> DistributionPlan:
    if not goals or income <= 0:
        return DistributionPlan(income, [], income,
                                f"No hay metas para ${income:.2f}")

    pct    = {1: 0.50, 2: 0.30, 3: 0.20}
    by_p   = {1: [], 2: [], 3: []}
    for g in goals:
        if g.target - g.current > 0:
            by_p[g.priority].append(g)

    items     = []
    remaining = income

    for pri in [1, 2, 3]:
        group = by_p[pri]
        if not group or remaining <= 0:
            continue
        bucket = min(remaining, income * pct[pri])
        share  = bucket / len(group)
        for g in group:
            needed = g.target - g.current
            amount = round(min(share, needed, remaining), 2)
            if amount <= 0:
                continue
            items.append(DistributionItem(
                goal_id=g.id,
                goal_name=g.name,
                amount=amount,
                wallet_address=g.wallet_address,
                reason=f"{amount/needed*100:.0f}% de lo que falta"
            ))
            remaining = round(remaining - amount, 2)

    lines = [f"Plan para ${income:.2f} cUSD:\n"]
    for it in items:
        lines.append(f"  - {it.goal_name}: ${it.amount:.2f}")
    if remaining > 0.01:
        lines.append(f"  - Sin asignar: ${remaining:.2f}")

    return DistributionPlan(income, items, remaining, "\n".join(lines))


if __name__ == "__main__":
    plan = calculate_distribution(300.0, DEMO_GOALS)
    print(plan.summary)
