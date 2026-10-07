# Public Anonymous Compute Laboratory

This repository is the public, neutral execution layer. It is designed to
run versioned public bundles without access to the private canonical
repository, private credentials, semantic mappings, raw source data, or
manuscript material.

## Operating model

1. The private repository exports a reviewed public bundle.
2. This repository receives the bundle, its schema, and a manifest containing
   hashes and neutral identifiers only.
3. GitHub Actions runs the public runtime locally from this repository.
4. Artifacts are downloaded and reconciled privately by hash; no reverse map is
   ever committed here.

The `compute-bridge-holdout-legacy.yml` workflow is retained only as an
explicit transitional compatibility path for the current holdout attempt.
New experiments must use
`compute-bridge-public.yml`, which has no private-repository checkout or
private secret dependency.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/PUBLIC_RELEASE_CONTRACT.md`](docs/PUBLIC_RELEASE_CONTRACT.md), and
[`public_bundle/README.md`](public_bundle/README.md).
