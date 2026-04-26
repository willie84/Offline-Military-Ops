import chromadb
# Data is saved to the specified folder on your machine
client = chromadb.PersistentClient(path="./my_local_db")

print(client)
