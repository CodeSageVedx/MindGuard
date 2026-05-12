from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from src.config import settings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import time


RESOURCES_DIR = './resources'
COLLECTION_NAME = 'mental_health_guidance'
QDRANT_URL = settings.QDRANT_URL
QDRANT_API_KEY = settings.QDRANT_API_KEY
OPENAI_API_KEY = settings.OPENAI_API_KEY

# load pdfs
documents = []
pdf_files = list(Path(RESOURCES_DIR).glob("**/*.pdf"))
for pdf_path in pdf_files:
    print(f"  Loading: {pdf_path.name}...")
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()

    # Add metadata to track source file
    for doc in docs:
        doc.metadata['source_file'] = pdf_path.name
    
    documents.extend(docs)
print(f"✅ Loaded {len(documents)} total pages")

# split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

chunks = text_splitter.split_documents(documents)
print(f"✅ Split into {len(chunks)} chunks")

# create embeddings
embeddings = OpenAIEmbeddings(
    api_key=OPENAI_API_KEY,
    model="text-embedding-3-small"
)

# initialize qdrant client
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=300  # Increase timeout to 5 minutes
)

# create collection if doesn't exist
try:
    client.get_collection(COLLECTION_NAME)
    print(f"📦 Collection '{COLLECTION_NAME}' already exists - deleting and recreating...")
    client.delete_collection(COLLECTION_NAME)
except:
    print(f"📦 Creating new collection '{COLLECTION_NAME}'")

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    )
)

# BATCH UPLOAD - Process in smaller chunks
BATCH_SIZE = 100  # Upload 100 documents at a time
total_chunks = len(chunks)
vectorstore = None

print(f"🚀 Uploading {total_chunks} chunks in batches of {BATCH_SIZE}...")

for i in range(0, total_chunks, BATCH_SIZE):
    batch = chunks[i:i+BATCH_SIZE]
    batch_num = (i // BATCH_SIZE) + 1
    total_batches = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"📦 Batch {batch_num}/{total_batches}: Uploading {len(batch)} chunks...")
    
    if i == 0:
        # First batch: create vectorstore
        vectorstore = QdrantVectorStore.from_documents(
            documents=batch,
            embedding=embeddings,
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            collection_name=COLLECTION_NAME
        )
    else:
        # Subsequent batches: add to existing vectorstore
        vectorstore.add_documents(batch)
    
    print(f"✅ Batch {batch_num}/{total_batches} complete ({i+len(batch)}/{total_chunks} total)")
    
    # Small delay to avoid overwhelming the server
    if i + BATCH_SIZE < total_chunks:
        time.sleep(1)

print(f"\n✅ Successfully uploaded all {total_chunks} chunks to collection '{COLLECTION_NAME}'")

# test retrieval
# print("\n🔍 Testing retrieval...")
# test_results = vectorstore.similarity_search("anxiety and stress management", k=3)
# for i, doc in enumerate(test_results, 1):
#     print(f"\n  Result {i}:")
#     print(f"    Source: {doc.metadata.get('source_file', 'Unknown')}")
#     print(f"    Content: {doc.page_content[:150]}...")

print("\n🎉 Upload complete!")