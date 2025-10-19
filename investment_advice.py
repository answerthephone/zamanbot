import yfinance as yf
import openai
import json
import asyncio
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def generate_investment_recommendations(risk_level: str):
    client = openai.AsyncOpenAI(api_key=openai.api_key)

    if risk_level == "low":
        return {
            "risk_level": "low",
            "recommendations": [
                {
                    "type": "bank_deposit",
                    "name": "Депозит 'Овернайт'",
                    "expected_yield_percent": 12,
                    "description": "Надёжный вариант с фиксированной доходностью и минимальным риском."
                },
                {
                    "type": "gov_bond",
                    "name": "Гособлигации РК",
                    "expected_yield_percent": 10,
                    "description": "Минимальный риск, стабильный доход."
                }
            ]
        }

    elif risk_level == "medium":
        stocks = ["AAPL", "MSFT", "GOOGL"]
        data = {ticker: yf.Ticker(ticker).history(period="1y")["Close"].iloc[-1] for ticker in stocks}
        return {
            "risk_level": "medium",
            "recommendations": [
                {"type": "ETF", "name": "SPY (S&P 500)", "expected_yield_percent": 15},
                {"type": "stocks", "companies": data}
            ]
        }

    elif risk_level == "high":
        # --- 1️⃣ Запрос к OpenAI ---
        prompt = (
            "Назови 5 американских акций, которые за последний месяц показали "
            "наибольший рост по цене. Ответь строго JSON списком тикеров, например: "
            '["NVDA", "TSLA", "AMD", "META", "AAPL"]'
        )

        response = await client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text = response.output_text.strip()
        print("🔍 OpenAI raw output:", text)

        # --- 2️⃣ Чистим Markdown-форматирование ---
        cleaned_text = (
            text.replace("```json", "")
                .replace("```", "")
                .strip()
        )

        # --- 3️⃣ Пробуем распарсить JSON ---
        try:
            trending_tickers = json.loads(cleaned_text)
            print("✅ Используем акции от OpenAI:", trending_tickers)
        except Exception as e:
            print(f"⚠️ Ошибка парсинга: {e}")
            print("Используем fallback тикеры.")
            trending_tickers = ["QBTS", "SMCI", "AI", "NVDA", "PLTR"]

        # --- 4️⃣ Получаем данные из yfinance ---
        stock_data = {}
        for ticker in trending_tickers:
            try:
                info = yf.Ticker(ticker).history(period="1mo")["Close"]
                stock_data[ticker] = {
                    "current_price": round(info.iloc[-1], 2),
                    "month_growth_percent": round(((info.iloc[-1] - info.iloc[0]) / info.iloc[0]) * 100, 2)
                }
            except Exception as e:
                print(f"⚠️ Ошибка при получении данных для {ticker}: {e}")
                continue

        # --- 5️⃣ Формируем финальный ответ ---
        return {
            "risk_level": "high",
            "recommendations": [
                {
                    "type": "stocks",
                    "companies": stock_data,
                    "description": "Самые быстрорастущие акции по данным рынка."
                },
                {
                    "type": "crypto",
                    "assets": {"BTC": "Bitcoin", "ETH": "Ethereum"},
                    "description": "Криптовалюты — высокая волатильность, высокая доходность."
                }
            ]
        }

    else:
        return {"error": "Unknown risk level."}

def get_risk_level_str(number: int):
    if number == 1:
        return "low"
    if number == 2:
        return "medium"
    if number == 3:
        return "high"
    return "medium"

# --- 🔹 Основной запуск ---
if __name__ == "__main__":
    # level надо взять у юзера, ллм пусть передаст значение или у самого юзера можно напрямую спросить
    level = input("Введите риск-профиль (low / medium / high): ")
    result = asyncio.run(generate_investment_recommendations(level))
    print(json.dumps(result, indent=2, ensure_ascii=False))

