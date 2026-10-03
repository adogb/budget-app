"""Write the API's OpenAPI schema to frontend/openapi.json.

Run by `npm run gen:api`, which then generates the TypeScript types from it.
"""

import json

from app.config import PROJECT_ROOT
from app.main import app

output = PROJECT_ROOT / "frontend" / "openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {output.relative_to(PROJECT_ROOT)}")
