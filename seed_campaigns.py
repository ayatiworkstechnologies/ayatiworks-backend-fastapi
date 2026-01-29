
import sys
import os

# Ensure we are running from backend directory
try:
    from app.database import SessionLocal
except ImportError:
    # Fallback if run from parent
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from app.database import SessionLocal

from app.models.auth import User
from app.models.client import Client, Lead, LeadSource, LeadStatus

def seed_campaigns():
    db = SessionLocal()
    try:
        print("Seeding Campaigns...")
        
        # Lead Source
        meta_source = db.query(LeadSource).filter_by(name="Meta").first()
        if not meta_source:
            meta_source = LeadSource(name="Meta", description="Facebook & Instagram Ads")
            db.add(meta_source)
            db.commit()
            print("  Created Lead Source: Meta")
        
        # Client (linked to Client User)
        client_user = db.query(User).filter_by(email="client@demo.com").first()
        if not client_user:
            print("  User client@demo.com NOT FOUND. Cannot create Client profile.")
            return

        client = db.query(Client).filter_by(email="client@demo.com").first()
        if not client:
            client = Client(
                name="Demo Client Co",
                email="client@demo.com",
                status="active",
                industry="Retail",
                manager_id=None  # Client User is not an employee. Internal manager can be assigned later.
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            print("  Created Client: Demo Client Co")
        else:
             print("  Client already exists")
        
        # Leads with Campaigns
        if client:
            campaigns = ["Q1 Promo", "Summer Sale", "Retargeting"]
            lead_count = 0
            for i, camp in enumerate(campaigns):
                for j in range(3): # 3 leads per campaign
                    lead_email = f"lead{i}{j}@example.com"
                    lead = db.query(Lead).filter_by(email=lead_email).first()
                    if not lead:
                        lead = Lead(
                            name=f"Lead {camp} #{j+1}",
                            email=lead_email,
                            client_id=client.id,
                            source_id=meta_source.id,
                            campaign=camp,
                            score=10 * (j+1) + 20,
                            status=LeadStatus.NEW.value
                        )
                        db.add(lead)
                        lead_count += 1
            db.commit()
            print(f"  Created {lead_count} Leads for Demo Client")
            
    except Exception as e:
        print(f"Error seeding campaigns: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_campaigns()
