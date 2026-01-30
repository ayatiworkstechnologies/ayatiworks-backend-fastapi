
import requests
import json

BASE_URL = "http://127.0.0.1:8001/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"

def test_update_blog():
    # 1. Login to get token
    # Assuming we have a user. If not, we might need to seed one or use existing.
    # I'll try with admin credentials if available, or create one.
    # For now, let's assume standard seed credentials if possible, or just try to hit it.
    
    # Actually, I need a valid token. 
    # Let's try to create a blog first, then update it.
    
    # 1. Login (Super Admin usually 'admin@example.com' / 'password') 
    # Adjust credentials as per seed.py or known state.
    
    login_data = {
        "email": "admin@ayatiworks.com",
        "password": "admin123"
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
            
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create a Blog
        create_payload = {
            "title": "Test Blog for Update",
            "slug": "test-blog-update-unique",
            "content": "<p>Initial content</p>",
            "category_id": 1, # Assuming cat 1 exists
            "status": "draft",
            "sections": [
                {"section_type": "content", "content": "<p>Section 1</p>", "heading": "Heading 1"}
            ]
        }
        
        # Create category first just in case
        cat_payload = {"name": "Test Cat", "slug": "test-cat"}
        requests.post(f"{BASE_URL}/blog-categories", json=cat_payload, headers=headers)
        
        print("Creating blog...")
        create_resp = requests.post(f"{BASE_URL}/blogs", json=create_payload, headers=headers)
        if create_resp.status_code != 201:
            print(f"Create failed: {create_resp.text}")
            # Try to get existing one if slug exists
            existing = requests.get(f"{BASE_URL}/blogs/test-blog-update-unique", headers=headers)
            if existing.status_code == 200:
                blog_id = existing.json()["id"]
                print(f"Using existing blog ID: {blog_id}")
            else:
                return
        else:
            blog_id = create_resp.json()["id"]
            print(f"Created blog ID: {blog_id}")
            
        # 3. Update the Blog (Simulate Frontend Payload)
        # Frontend sends: sections list WITHOUT IDs (because it destructures them out)
        # It sends: { ...rest, section_type: type, order: idx }
        
        update_payload = {
            "title": "Updated Title",
            "slug": "test-blog-update-unique",
            "content": "<p>Updated content</p>",
            "sections": [
                 # Section 1 (Update) - No ID
                {"section_type": "content", "content": "<p>Section 1 Updated</p>", "heading": "Heading 1 Updated", "order": 0},
                 # Section 2 (New) - No ID
                {"section_type": "image", "image": "http://example.com/img.jpg", "image_caption": "New Image", "order": 1}
            ]
        }
        
        print("\nUpdating blog with payload (No IDs in sections)...")
        update_resp = requests.put(f"{BASE_URL}/blogs/{blog_id}", json=update_payload, headers=headers)
        
        print(f"Update Status: {update_resp.status_code}")
        print(f"Update Response: {update_resp.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_update_blog()
