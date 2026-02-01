
import urllib.request
import json
import traceback

try:
    print("Testing GET /api/v1/blogs...")
    req = urllib.request.Request('http://localhost:8000/api/v1/blogs')
    # Add a mock authorization header if needed, but let's try public first
    
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.getcode()}")
        data = json.loads(response.read().decode('utf-8'))
        print("Response Keys:", list(data.keys()))
        
        if 'items' in data:
            print(f"Items Count: {len(data['items'])}")
            if len(data['items']) > 0:
                print("First Item Sample:", json.dumps(data['items'][0], indent=2))
        else:
            print("Response raw:", data)

except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Failed to connect: {e}")
    traceback.print_exc()
