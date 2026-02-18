from app.database import SessionLocal
from app.models.client import Client
from app.models.client_module import ClientModule

db = SessionLocal()
try:
    client = db.query(Client).filter(Client.slug == "swaram").first()
    if not client:
        print("Client 'swaram' NOT FOUND")
    else:
        print(f"Client: {client.name} (ID: {client.id})")
        print(f"API Key: {client.api_key}")
        
        module = db.query(ClientModule).filter(
            ClientModule.client_id == client.id, 
            ClientModule.slug == "contact"
        ).first()
        
        if not module:
            print("Module 'contact' NOT FOUND for this client")
        else:
            print(f"Module: {module.name} (ID: {module.id})")
finally:
    db.close()
