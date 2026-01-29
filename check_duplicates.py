
from app.main import app
from fastapi.utils import generate_unique_id

seen_ids = set()
duplicates = []

for route in app.routes:
    if hasattr(route, "operation_id"):
        op_id = route.operation_id or route.name
        if op_id in seen_ids:
            duplicates.append(op_id)
        seen_ids.add(op_id)

print(f"Duplicates found: {duplicates}")
