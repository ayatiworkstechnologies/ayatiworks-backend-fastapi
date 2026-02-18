import sys
import os

# Ensure backend root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from app.database import SessionLocal
# Import models
from app.models.client import Client
from app.models.client_module import ClientModule

def check_data():
    db = SessionLocal()
    try:
        print("\n--- Checking Client 'swaram' ---")
        client = db.query(Client).filter(Client.slug == "swaram").first()
        if not client:
            print("❌ Client 'swaram' NOT FOUND")
        else:
            print(f"✅ Client Found: {client.name} (ID: {client.id})")
            print(f"🔑 API Key: {client.api_key}")
            
            print("\n--- Checking Module 'contact' ---")
            module = db.query(ClientModule).filter(
                ClientModule.client_id == client.id, 
                ClientModule.slug == "contact"
            ).first()
            
            if not module:
                print("❌ Module 'contact' NOT FOUND for this client")
            else:
                print(f"✅ Module Found: {module.name} (ID: {module.id})")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_data()
