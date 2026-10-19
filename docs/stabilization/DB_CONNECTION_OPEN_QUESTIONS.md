# Database connection layer owner decisions

These choices remain configurable or documented rather than being changed without the product owner's policy decision.

1. **Private and local database targets:** Should production permit RFC 1918, loopback, or link-local destinations for customer-managed databases? Current protection rejects them unless the existing explicit private-network setting enables them. Confirm whether this exception should be tenant-scoped, environment-scoped, or disabled entirely.
2. **Encryption key ownership and rotation:** Which secret manager owns `DATA_ENCRYPTION_KEY`, how will key versions be retained during rotation, and what migration/back-up plan is required for stored credentials? Existing legacy plaintext values still decrypt for compatibility; decide when/how to migrate them at rest.
3. **Demo configuration:** Which environment is used for the business-owner demo, and may it use only managed SQLite sample data? Do not use a shared/default encryption key or production customer credentials.
4. **Pool and worker budgets:** What are the production worker/process count and per-customer DB connection ceilings? SQLAlchemy pool settings are per engine and per process; the current bounded engine cache and 32 SQL workers do not define a safe aggregate connection budget for every deployment.
5. **100-user load profile:** Define whether 100 means authenticated sessions, simultaneous DB queries, or mixed API traffic, and provide an owner-approved synthetic load environment. No load test or external DB connection was run in this task.
6. **MongoDB data masking:** Confirm which document fields are sensitive and whether preview/query results should use a deny-list, allow-list, or configured per-tenant policy before adding Mongo-specific masking.
7. **Legacy direct-driver pools:** The existing PostgreSQL/MySQL/Mongo pool helpers remain in `database_connection_service.py`. Confirm whether any deployment still calls them; if so, decide whether to remove them or replace them with the shared bounded pool abstraction.

No actual private, loopback, production, or cloud database endpoint was accessed during this task.
