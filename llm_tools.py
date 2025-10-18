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
        "name": "get_personal_finance_analytics",
        "description": "Get personal finance analytics.",
        "parameters": {
            "type": "object",
            "properties": {
            },
            "required": [],
            "additionalProperties": False,
        },
    }
]
