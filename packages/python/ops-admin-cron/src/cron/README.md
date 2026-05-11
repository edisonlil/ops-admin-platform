# Cron

Cron owns platform and tenant scheduled task definitions, schedules, run
records, execution attempts, and external scheduler bindings.

Runtime code must not initialize or repair storage implicitly. Run
`python scripts/init_cron.py` before enabling cron APIs or workers in an
environment.

The domain/application model is scheduler-agnostic. Built-in scheduling should
be provided by infrastructure adapters such as APScheduler, and distributed
scheduling can be added through adapters such as Temporal without changing the
HTTP contract.
