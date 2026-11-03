# Verification record

## Included automated tests

`python verify.py` runs 10 backend integration tests using temporary databases. They cover CSRF, permissions, plan snapshot isolation, synchronization/version conflicts, recorder/device ownership, session uniqueness, measurements/dates, restart persistence and single-trainer connections.

## Earlier development checks

Local Chrome checks covered login, workout preparation, local saves, offline reload/recovery, offline completion, reconnect/sync, duplicate-free uploads and shared history after switching to the linked account.

Form checks covered profiles, measurements and corrections, template assignments, past entries, blank sessions, additional exercises, completion and record correction. English localization was checked across 18 pages or states, including desktop and 390px mobile layouts. No horizontal page overflow or uncaught JavaScript errors were observed in those completed checks.

These are recorded development checks, not a portable browser test suite included in this repository. Preview images show fictional sample data.

## Outstanding acceptance work

- Physical iPhone Safari and Android Chrome testing.
- Public HTTPS deployment, persistent hosted storage and restart/recovery.
- Classroom multi-device rehearsal, backup operations and production hardening.

Desktop checks do not constitute production or final mobile acceptance.
