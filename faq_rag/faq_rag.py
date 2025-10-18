import sys
from functools import lru_cache
from dotenv import load_dotenv
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

load_dotenv()

embed_model = OpenAIEmbedding(model="text-embedding-3-small")
storage_context = StorageContext.from_defaults(persist_dir="faq_rag/rag_db")
index = load_index_from_storage(storage_context, embed_model=embed_model)

llm = OpenAI(model="gpt-4o-mini")
query_engine = index.as_query_engine(llm=llm)


def ask_faq_unoptimized(query):
    return query_engine.query(query)

@lru_cache(maxsize=1024)
def ask_faq(query: str):
    return str(ask_faq_unoptimized(query))

if __name__ == "__main__":
    # Optional CLI query
    if len(sys.argv) > 1:
        response = ask_faq(sys.argv[1])
        print("Chatbot:", response)
        print()

    # Interactive mode
    while True:
        user_input = input("User: ")
        response = ask_faq(user_input)
        print("Chatbot:", response)
        print()
