# Audit Logging

The audit logging context records platform runtime events without coupling business modules
to storage details. It stores system, operation, API, SQL, and visitor logs in the primary
database through an in-process bounded queue and a background batch worker.

First-version constraints:

- Logs are written asynchronously to avoid slowing the main request path.
- API and audit settings endpoints are excluded from collection to prevent recursive logging.
- SQL collection records only slow SQL and error SQL. Parameters are never stored.
- IP plaintext retention is controlled by platform settings; long-term filtering can rely on
  `ip_hash`.
- Tenant admins can view permitted logs but only platform admins can change settings.
