# ITAD Core

Minimal backend service for ITAD operations compliance data.

## Architecture

- **SoR (System of Record):** ITAD Core owns BOLs, Receiving Weight Records, processing, chain-of-custody, evidence, reconciliation, inventory, shipments, disposition, certificates, settlement.
- **Integration:** External ID mapping for Odoo references, idempotency keys, correlation IDs.
- **Stack:** FastAPI, SQLAlchemy, Postgres, Alembic.

## Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Set environment variables:
   ```bash
   export ITAD_CORE_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/itad_core
   export ITAD_CORE_PORT=8001
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

4. Seed demo data:
   ```bash
   python -m app.scripts.seed_demo
   ```

5. Start the service:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Docker

```bash
docker-compose -f docker-compose.itad-core.yml up --build
```

## API Examples

### Create BOL
```bash
curl -X POST "http://localhost:8001/api/v1/bol" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-bol-123" \
  -H "X-Request-Id: req-123" \
  -H "X-Correlation-Id: corr-123" \
  -d '{
    "bol_number": "BOL-TEST-001",
    "source_type": "PICKUP",
    "customer_snapshot_json": {"name": "Test Customer", "id": "odoo-cust-123"}
  }'
```

### Create Receiving Weight Record
```bash
curl -X POST "http://localhost:8001/api/v1/receiving-weight-records" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-recv-123" \
  -H "X-Request-Id: req-124" \
  -H "X-Correlation-Id: corr-124" \
  -d '{
    "bol_id": "uuid-from-bol",
    "occurred_at": "2023-01-01T10:00:00Z",
    "container_type": "PALLET",
    "quantity": 1,
    "gross_weight": 100.0,
    "tare_weight": 10.0,
    "net_weight": 90.0,
    "scale_id": "SCALE-001",
    "receiver_name": "John Doe"
  }'
```

## Testing

```bash
pytest
```