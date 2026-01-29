"""
Bulk update script to replace HTTPException with custom exceptions.
This script systematically updates all API modules.

Run: python update_exceptions.py
"""

import re
import os
from pathlib import Path

# Map of HTTPException patterns to custom exceptions
EXCEPTION_MAPPINGS = [
    # 404 Not Found patterns
    (
        r'raise HTTPException\(\s*status_code=status\.HTTP_404_NOT_FOUND,\s*detail="(\w+) not found"\s*\)',
        r'raise ResourceNotFoundError("\1", \1_id)'
    ),
    (
        r'raise HTTPException\(\s*status_code=404,\s*detail="(\w+) not found"\s*\)',
        r'raise ResourceNotFoundError("\1", \1_id)'
    ),
    # 401 Unauthorized patterns
    (
        r'raise HTTPException\(\s*status_code=status\.HTTP_401_UNAUTHORIZED,\s*detail="Invalid (\w+)"\s*\)',
        r'raise InvalidCredentialsError("Invalid \1")'
    ),
    # 403 Forbidden patterns
    (
        r'raise HTTPException\(\s*status_code=status\.HTTP_403_FORBIDDEN,\s*detail="([^"]+)"\s*\)',
        r'raise PermissionDeniedError("\1")'
    ),
]

def add_import_if_missing(content: str) -> str:
    """Add custom exception imports if not present."""
    if 'from app.core.exceptions import' in content:
        return content
    
    # Find the last import statement
    import_pattern = r'(from app\.[\w.]+ import [^\n]+\n)'
    matches = list(re.finditer(import_pattern, content))
    
    if matches:
        last_import = matches[-1]
        insertion_point = last_import.end()
        
        import_statement = """from app.core.exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ValidationError,
    BusinessLogicError
)
"""
        content = content[:insertion_point] + import_statement + content[insertion_point:]
    
    return content

def update_file(filepath: Path) -> bool:
    """Update a single file with custom exceptions."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add imports if needed
        content = add_import_if_missing(content)
        
        # Apply exception replacements
        for pattern, replacement in EXCEPTION_MAPPINGS:
            content = re.sub(pattern, replacement, content)
        
        # Manual replacements for common patterns
        content = content.replace(
            'raise HTTPException(\n            status_code=status.HTTP_404_NOT_FOUND,\n            detail="Employee not found"\n        )',
            'raise ResourceNotFoundError("Employee", employee_id)'
        )
        
        content = content.replace(
            'raise HTTPException(\n            status_code=status.HTTP_404_NOT_FOUND,\n            detail="Project not found"\n        )',
            'raise ResourceNotFoundError("Project", project_id)'
        )
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def main():
    """Update all API files."""
    api_dir = Path(__file__).parent / 'app' / 'api' / 'v1'
    
    files_to_update = [
        'employees.py',
        'attendance.py',
        'leaves.py',
        'projects.py',
        'clients.py',
        'invoices.py',
        'notifications.py',
        'companies.py',
        'teams.py',
        'reports.py',
        'dashboard.py',
    ]
    
    updated_count = 0
    for filename in files_to_update:
        filepath = api_dir / filename
        if filepath.exists():
            if update_file(filepath):
                print(f"✓ Updated {filename}")
                updated_count += 1
            else:
                print(f"- No changes needed for {filename}")
        else:
            print(f"✗ File not found: {filename}")
    
    print(f"\n✅ Updated {updated_count} files")

if __name__ == "__main__":
    main()
