import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_list_blogs():
    print("Testing GET /blogs...")
    try:
        response = requests.get(f"{BASE_URL}/blogs")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: Retrieved {data['total']} blogs")
            if data['items']:
                first_blog = data['items'][0]
                print(f"First blog ID: {first_blog['id']}")
                print(f"First blog slug: {first_blog.get('slug')}")
                return first_blog
            else:
                print("No blogs found.")
                return None
        else:
            print(f"Failed: Status {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_get_blog_by_id(blog_id):
    if not blog_id:
        return
        
    print(f"\nTesting GET /blogs/{blog_id} (ID)...")
    try:
        response = requests.get(f"{BASE_URL}/blogs/{blog_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: Retrieved blog {data['id']}")
            # Check nested fields
            print(f"Author Profile: {data.get('author_profile')}")
            print(f"Category: {data.get('category')}")
        else:
            print(f"Failed: Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

def test_get_blog_by_slug(slug):
    if not slug:
        return

    print(f"\nTesting GET /blogs/{slug} (Slug)...")
    try:
        response = requests.get(f"{BASE_URL}/blogs/{slug}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: Retrieved blog {data['id']} by slug")
        else:
            print(f"Failed: Status {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    blog_data = test_list_blogs()
    if blog_data:
        blog_id = blog_data['id']
        blog_slug = blog_data.get('slug')
        
        test_get_blog_by_id(blog_id)
        
        if blog_slug:
            test_get_blog_by_slug(blog_slug)
