# Bank services
services = [
    {
        "product_name": "Овернайт",
        "product_type": "Депозитный",
        "expected_yield_percent": 12,
        "max_amount_tenge": 100_000_000,
        "min_amount_tenge": 1_000_000,
        "min_term_months": 1,
        "max_term_months": 12
    },
    {
        "product_name": "Выгодный",
        "product_type": "Депозитный",
        "expected_yield_percent": 17,
        "max_amount_tenge": 100_000_000,
        "min_amount_tenge": 500_000,
        "min_term_months": 3,
        "max_term_months": 12
    }
]

def generate_saving_strategies(financial_goal, current_balance, monthly_savings):
    strategies = []

    for service in services:
        min_amount = service.get("min_amount_tenge", 0)
        interest_rate = service.get("expected_yield_percent", 0) / 100  # convert to decimal

        if current_balance < min_amount:
            # Skip strategies if current balance is below minimum
            continue

        balance = current_balance
        months = 0

        # Simulate monthly growth
        while balance < financial_goal and months < service.get("max_term_months", 1200):
            balance += monthly_savings
            # Apply monthly interest (assume annual rate divided by 12)
            balance += balance * (interest_rate / 12)
            months += 1

        if balance >= financial_goal:
            strategies.append({
                "product_name": service["product_name"],
                "estimated_months_to_goal": months,
                "final_amount": round(balance, 2)
            })

    # Sort strategies by how fast they reach the goal
    strategies.sort(key=lambda x: x["estimated_months_to_goal"])
    return strategies
