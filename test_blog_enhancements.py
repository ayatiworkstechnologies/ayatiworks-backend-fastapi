
import httpx
import time

BASE_URL = "http://localhost:8001/api/v1"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"

def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    print("1. Login...")
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    
    data = resp.json()
    token = data["access_token"]
    user_id = data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login OK.")
    
    # 2. Blog Category CRUD
    print("\n--- Testing Blog Category CRUD ---")
    cat_data = {
        "name": f"Test Category {int(time.time())}",
        "slug": f"test-category-{int(time.time())}",
        "description": "Verification category"
    }
    resp = client.post("/blog-categories", json=cat_data, headers=headers)
    print(f"Create Category: {resp.status_code}")
    if resp.status_code == 201:
        cat_id = resp.json()["id"]
        print(f"Category Created ID: {cat_id}")
        
        # Update
        resp = client.put(f"/blog-categories/{cat_id}", json={"name": "Updated Category Name"}, headers=headers)
        print(f"Update Category: {resp.status_code}")
        
    # 3. Blog Author CRUD
    print("\n--- Testing Blog Author CRUD ---")
    author_data = {
        "user_id": user_id,
        "display_name": "Admin Author",
        "bio": "Expert blog writer.",
        "social_links": {"twitter": "@admin", "linkedin": "admin-linkedin"}
    }
    # Might already exist from previous test runs if database not reset, so we'll handle both cases
    resp = client.post("/blog-authors", json=author_data, headers=headers)
    print(f"Create Author: {resp.status_code}")
    author_id = None
    if resp.status_code == 201:
        author_id = resp.json()["id"]
        print(f"Author Created ID: {author_id}")
    elif resp.status_code == 400:
        print("Author profile already exists, fetching existing authors...")
        resp = client.get("/blog-authors", headers=headers)
        if resp.status_code == 200 and resp.json():
            author_id = resp.json()[0]["id"]
            print(f"Using existing Author ID: {author_id}")

    if author_id:
        # Update
        resp = client.put(f"/blog-authors/{author_id}", json={"bio": "Highly experienced writer."}, headers=headers)
        print(f"Update Author: {resp.status_code}")

    # 4. Blog Post with Category and (implicitly) Author
    print("\n--- Testing Blog Post with Category ---")
    blog_data = {
        "title": f"Enhanced Blog Post {int(time.time())}",
        "slug": f"enhanced-post-{int(time.time())}",
        "content": "This post uses categories and services.",
        "category_id": cat_id if 'cat_id' in locals() else None,
        "status": "published"
    }
    resp = client.post("/blogs", json=blog_data, headers=headers)
    print(f"Create Blog Post: {resp.status_code}")
    if resp.status_code == 201:
        print("Blog Post Created successfully using services!")

if __name__ == "__main__":
    run_tests()
