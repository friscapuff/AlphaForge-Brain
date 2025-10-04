# Dataset Location Policy

For local development and tests, place canonical datasets under the repository root `data/` directory (e.g., `./data/NVDA_5y.csv`).

Do not commit large datasets inside the package. Test fixtures support falling back to `src/domain/data/` only for small seed files, but the preferred location is `./data`.

If both locations exist, tests use `./data` by default.
