from pymongo import MongoClient

uri = "mongodb+srv://StarFront:eD3fisl30Ngd9Bi5@iceman.kzlllr6.mongodb.net/?retryWrites=true&w=majority&appName=iceman"

client = MongoClient(uri)

db = client["llano_grande"]

huevos_collection = db["huevos"]

