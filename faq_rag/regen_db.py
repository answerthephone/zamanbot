from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.openai import OpenAIEmbedding
import os

load_dotenv()

DATA_DIR = "faq_rag/data"
PERSIST_DIR = "faq_rag/rag_db"

print("📂 Loading documents from:", DATA_DIR)
documents = SimpleDirectoryReader(DATA_DIR, recursive=True, filename_as_id=True).load_data()

embed_model = OpenAIEmbedding(model="text-embedding-3-small")

if os.path.exists(PERSIST_DIR):
    print("🧠 Loading existing index...")
    storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
    index = load_index_from_storage(storage_context, embed_model=embed_model)
else:
    print("✨ Creating new index...")
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    print("✅ Initial index created and saved.")
    exit(0)

print("🔄 Refreshing index with changed or new documents...")
index.refresh_ref_docs(documents)
index.storage_context.persist(persist_dir=PERSIST_DIR)

print("\n📄 Documents currently in index:")
for doc_id in index.ref_doc_info.keys():
    print(f"  - {doc_id}")

print("\n✅ Index update complete.")
