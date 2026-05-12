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

## Built-in Worker

Initialize storage explicitly:

```bash
python scripts/init_cron.py
```

Run the built-in APScheduler worker:

```bash
python scripts/run_cron_worker.py
```

The worker loads enabled tasks that have schedules, registers them in
APScheduler, creates `cron_runs` and `cron_attempts` when they fire, dispatches
the task command, and stores the command result on `cron_runs.result_json`.

## Built-in Commands

Default worker dispatch uses `cron.infrastructure.commands.registry`.

Available commands:

- `system.health.snapshot`: calls the system health application service and
  stores the resulting health payload on the cron run.

Additional commands should be registered through the command registry and kept
behind the `TaskDispatcher` port. Command implementations belong in
`infrastructure/commands` when they call other contexts or framework adapters.
