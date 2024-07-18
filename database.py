from chromadb import Client
from chromadb.utils import embedding_functions
import chromadb
import csv
import os

from dotenv import load_dotenv
load_dotenv()

def createDB():
    chroma_client = Client()
    openai_ef= embedding_functions.OpenAIEmbeddingFunction(
        api_key= os.environ.get("OPENAI_API_KEY"),
        model_name= "text-embedding-ada-002"
    )
    collection = chroma_client.create_collection(name="my_items", embedding_function=openai_ef)
    client = chromadb.PersistentClient(path="vectordb")
    return collection

def addItemsDB(collection):
    names = []
    urls = []
    images = []
    ids = []
    id = 1

    with open('./items.csv') as file:
        lines = csv.reader(file)
        for i, line in enumerate(lines):
            if i == 0:
                continue  # Skip header
            names.append(line[0])
            urls.append(line[1])
            images.append(line[2])
            ids.append(str(id))
            id += 1
    
    collection.add(
        documents=names,
        metadatas=[{"url": url, "image": image} for url, image in zip(urls, images)],
        ids=ids
    )
    
 
def retrieve(collection, item):
    result = collection.query(
        query_texts=[item],
        n_results = 1,
        include=['documents', 'metadatas']
    )
    return result

def dropDB(collection):
    collection.drop()

# collection = createDB()
# addItemsDB(collection)
# result = retrieve(collection, "e-")

# print(result["ids"][0][0])
# print(result["documents"][0][0])
# print(result["metadatas"][0][0]["image"])
# print(result["metadatas"][0][0]["url"])