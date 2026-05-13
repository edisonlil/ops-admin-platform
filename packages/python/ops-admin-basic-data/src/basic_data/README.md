# Basic Data

`basic_data` owns tenant-scoped basic business data for the platform.

The first capability is business dictionary management: dictionary types and dictionary items. Automatic sequence rules are planned as a separate capability inside the same bounded context, but are not part of the first implementation.

Runtime request handling must only verify that persistence resources already exist. Schema creation and seed application are explicit initialization tasks exposed through `basic_data.entrypoints:init_tasks` and the `scripts/init_basic_data.py` helper.

HTTP APIs are mounted under `/basic-data` and return the unified response envelope from the `system` context.
