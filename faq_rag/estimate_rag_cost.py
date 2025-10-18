import os
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader
from openai import OpenAI

MODEL = "text-embedding-3-small"
PRICE_PER_TOKEN = {
    "text-embedding-3-small": 0.02 / 1_000_000,
}
DATA_DIR = "faq_rag/data"

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
documents = SimpleDirectoryReader(DATA_DIR, recursive=True).load_data()
texts = [doc.text for doc in documents]

def count_tokens(text, model=MODEL):
    response = client.embeddings.create(input=[text], model=model)
    return response.usage.total_tokens

print()
print()

total_tokens = 0
for i, text in enumerate(texts, start=1):
    tokens = count_tokens(text)
    total_tokens += tokens
    print(f"Document {i}: {tokens} tokens")

cost = total_tokens * PRICE_PER_TOKEN[MODEL]

print(f"\nModel: {MODEL}")
print(f"Total tokens: {total_tokens:,}")
print(f"Estimated cost: ${cost:.4f} USD")
