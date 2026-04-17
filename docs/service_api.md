## Service API Layer

The FastAPI backend is intentionally split into three readable layers:

- `service_api/routes`
  Thin HTTP endpoints only. Routes parse request data, call one application service, and return response schemas.
- `application/services`
  Business operations such as delivery updates, pallet movement, document upload coordination, print instructions, and print jobs.
- `data/repositories`
  Small explicit database access helpers. Repositories do not contain HTTP logic or UI concerns.

### Why this structure was chosen

- The desktop client talks to stable service contracts instead of reading database tables directly.
- Business rules stay in Python service classes that an internal IT team can test and maintain.
- API endpoints remain easy to scan because they are intentionally thin.
- Database access stays explicit and migration-friendly because it is not hidden behind complex abstractions.

### Current endpoint groups

- `delivery-slips`
  Retrieval and update of delivery slips.
- `pallets`
  Retrieval, update, loading, and movement operations for pallets.
- `documents`
  Document metadata queries and upload coordination.
- `printing`
  Print instruction and print job operations.
- `audit-logs`
  Explicit audit log write support for business actions.
- `health`
  Basic service health endpoint for internal monitoring and deployment checks.

### Local startup

Example local startup command:

```powershell
c:\python314\python.exe -m uvicorn logistics_app.service_api.main:app --host 0.0.0.0 --port 8000
```

The service reads database, storage, printer, and environment settings from the shared application configuration. That means IT can move the backend to another environment without editing route or service code.
