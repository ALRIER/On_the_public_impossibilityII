# Anonymous public/private architecture

## Boundary

The private repository is the scientific source of truth. It owns semantic
target names, source provenance, raw inputs, parameter interpretation,
manuscript claims, and the decoding registry.

The public repository is an independently executable laboratory. It owns only
neutral IDs, numeric public inputs, the reviewed execution bundle, schemas,
tests, controls, and neutral result artifacts.

The public repository must never contain:

- a private GitHub token, private-repository checkout, or private path;
- a raw external source response;
- country/source/indicator names when the experiment is meant to be neutral;
- semantic target or parameter names;
- the private ID-decoding registry;
- a script that can reconstruct the private mapping from public files.

## Release flow

```text
private export -> leak scan -> manifest + hashes -> public release
      ^                                                   |
      |                                                   v
private reconciliation <- artifact download <- public run
```

Every release is immutable. A new bundle revision is used for a new run; an
existing run is never silently replaced. The private side records the public
commit, bundle digest, control digest, workflow ID, artifact names, and final
reconciliation status.

## Decoding registry

The semantic map is private-only and versioned there by experiment and bundle
revision. It is not a temporary file copied to the public repository. Public
IDs are stable within one experiment family but may be rotated between
families where linkage risk matters.

## Independence rule

The public workflow must be able to run from a fresh clone with only public
repository contents and public package dependencies. A private checkout may
be used by a transitional legacy workflow, but it is not an acceptable
dependency for a new experiment.

## Future task contract

Each task is a public runtime adapter with:

- a task ID and schema version;
- an explicit shard domain;
- a public input manifest and SHA-256 digest;
- deterministic seed and replication metadata;
- neutral CSV/JSON output schema;
- a receipt recording commit, bundle revision, shard, and input hashes.

Tasks are registered in `runtime/manifest.json`. Unknown task IDs and
unregistered files fail closed.
