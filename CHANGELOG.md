# Flower 2.1.0

## Features

- Added read-only mode for the UI and API #1468 by @MrEarle.
- Updated the UI with a responsive design.
- Added persistent dark mode with light and system theme options.
- Added a browser favicon #1502 by @rolfws.
- Improved task search with boolean operators and field filters.
- Preserved task-table preferences across visits #1333 by @fretman92.
- Added TLS support for Redis Sentinel #1327 by @cyberjunk.
- Added AMQPS support for RabbitMQ connections by @borland667.
- Updated and auto-provisioned the Grafana dashboard.
- Enabled API access in the Docker Compose demo.

## Performance and reliability

- Moved blocking broker and control operations off the I/O loop.
- Made Redis queue inspection asynchronous and pipelined.
- Prevented duplicate worker inspections.
- Fixed broker connection leaks #1490.
- Purged stale offline-worker Prometheus metrics #1128.
- Persisted dashboard counters across restarts #787.
- Improved handling of missing custom configuration files.
- Fixed startup banner output when using a dynamic port #1449.
- Fixed worker active-task totals when counts are null #1511 by @M4RC0Sx.
- Fixed undefined worker pool grow and shrink values #1324 by @daydaychen.

## Bug fixes

- Fixed Redis SSL configurations #1177.
- Fixed percent-encoded IPv6 broker addresses #1220.
- Stopped exposing broker alternate URLs in worker statistics #1512.
- Fixed broker page rendering when queue inspection fails #1501 by @alexei.
- Fixed autoscaling response interpolation #1427 by @funkyrailroad.
- Improved GitHub OAuth errors when email access is unavailable #1486 by @bysiber.
- Prevented authentication failures while rendering error pages #1268, #1499.
- Fixed task search for non-string values #1401.
- Fixed task state filters to require the state prefix #1516 by @AleksaMCode.
- Fixed worker names in timeout and rate-limit error responses #1506 by @phanky1.

## Documentation

- Documented custom authentication providers #1344.
- Corrected the GitLab authentication handler name #1325 by @Saluev.
- Fixed the persistent database CLI example #1326 by @hatamiarash7.
- Fixed the Grafana example URL #1345 by @NiclasvanEyk.
- Corrected the nginx reverse-proxy example by @titovanton.
- Added the GitHub repository link to the documentation by @PamelaM.
- Corrected the documented database filename #1494 by @WilliamDEdwards.
- Corrected the documented max tasks default #1415 by @masahiro331.
- Clarified task API options #1269.

## Compatibility and packaging

- Added Python 3.13 and 3.14 support; Python 3.10+ is now required #1439.
- Added Python 3.12 support and package classification #1334 by @foarsitter.
- Removed obsolete Python versions from CI and tox #1442 by @auvipy.
- Added Celery 5.6 CI coverage.
- Updated the tox compatibility matrix #1451, #1452 by @auvipy.
- Raised the minimum Tornado version to 6.5.7 #1439.
- Upgraded OpenSSL in the Docker image #1483 by @matheusnascgomes.
- Added Dependabot management for GitHub Actions #1383 by @cclauss.
- Improved CI linting reliability #1445 by @Nusnus.
- Updated .gitignore to exclude local Python version files #1444 by @Nusnus.
- Ran unit tests before lint checks #1447 by @auvipy.
- Removed the obsolete Travis CI configuration by @auvipy.

**Full changelog:** [v2.0.1...v2.1.0](https://github.com/mher/flower/compare/v2.0.1...v2.1.0)
