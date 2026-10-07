# Public release contract

The private exporter must publish a reviewed bundle directory with this
layout:

```text
public_bundle/
  manifest.json
  inputs/
  runtime/
  schemas/
  tests/
```

`manifest.json` must contain the bundle revision, schema versions, file
SHA-256 values, allowed task IDs, shard domains, and a statement that all
inputs are neutral. It must not contain semantic names or private paths.

The public control file selects one registered task and its shards. It may
refer only to paths inside the public checkout. Relative paths are resolved
from the control file's directory exactly once.

Outputs must include:

- `task_receipt.json`;
- the public bundle revision and input digest;
- the public commit SHA;
- shard and seed metadata;
- neutral result rows only.

The private reconciler must reject artifacts whose bundle digest, control
digest, task ID, shard, schema, or commit does not match the pre-registered
run.
