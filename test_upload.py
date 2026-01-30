import requests
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_upload_image():
    print("Testing image upload...")
    
    # Create a dummy image file
    file_path = "test_image.jpg"
    with open(file_path, "wb") as f:
        f.write(b"dummy image content")
        
    try:
        # First login to get a token (assuming there's a test user or something)
        # For now, let's see if it fails with 401 as expected or something else
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{BASE_URL}/uploads/images", files=files)
            
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    test_upload_image()
