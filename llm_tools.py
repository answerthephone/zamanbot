tools = [
    {
        "type": "function",
        "strict": True,
        "name": "generate_saving_strategies",
        "description": "Generate saving strategies based on bank's services.",
        "parameters": {
            "type": "object",
            "properties": {
                "financial_goal": {
                    "type": "integer",
                    "description": "The client's financial goal in KZT.",
                },
                "current_balance": {
                    "type": "integer",
                    "description": "The client's current balance in KZT.",
                },
                "monthly_savings": {
                    "type": "integer",
                    "description": "How much the client saves monthly.",
                },
            },
            "required": ["financial_goal", "current_balance", "monthly_savings"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "strict": True,
        "name": "get_user_financial_summary",
        "description": "Get summary of a user's income and expenses over the last_n_days.",
        "parameters": {
            "type": "object",
            "properties": {
                "last_n_days": {
                    "type": "integer",
                    "description": "Number of days to look back for the summary."
                }
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "strict": True,
        "name": "get_investment_recommendations",
        "description": "Get investment recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "risk_level": {
                    "type": "integer",
                    "description": "from 1 to 3 where 1 is low, 2 is medium and 3 is high."
                }
            },
            "required": ["risk_level"],
            "additionalProperties": False,
        },
    }
]

def get_tools_summary():
    summary = []
    for tool in tools:
        summary.append({
            "name": tool.get("name"),
            "description": tool.get("description")
        })
    return summary
