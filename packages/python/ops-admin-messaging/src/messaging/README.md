# Messaging

Messaging owns platform message intents, in-app inbox records, channel deliveries,
templates, and channel account configuration.

Runtime code must not initialize or repair storage implicitly. Run
`python scripts/init_messaging.py` before enabling messaging APIs in an
environment.
