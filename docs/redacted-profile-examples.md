# Redacted Reconstructed Profile Examples

## profile_example_1

- Cluster: `hybrid_o_000230`
- Majority owner-like label: `[ORG]`
- Requests: 48

### Fields

- `languages`: `['go', 'java', 'javascript', 'python', 'typescript']`
- `frameworks`: `['jest']`
- `package_managers`: `['maven', 'npm', 'pip', 'yarn']`
- `build_tools`: `['go test', 'make', 'maven']`
- `repo_names`: `['[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]']`
- `ci_cd_systems`: `['circleci']`
- `service_names`: `['[SERVICE_NAMES]']`
- `internal_domains`: `['[DOMAIN]', '[DOMAIN]', '[DOMAIN]']`

### Evidence

- `frameworks` = `jest` from `[REQ]`: > @elastic/synthetics@0.0.1-alpha.14 test > npm run test:unit && npm run test:browser-service --testPathPattern=__tests__/dsl/journey.test.ts > @elastic/synthetics@0.0.1-alpha.14 test:unit > jest Determining test suites to run... Running without BrowserService
- `package_managers` = `pip` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `package_managers` = `npm` from `[REQ]`: src/helpers.ts:659:54 - error TS2698: Spread types may only be created from object types. 659 : serializer.serialize({ doc: chunk, ...secondArg }) ~~~~~~~~~~~~ Found 1 error in src/helpers.ts:659 npm notice npm notice New major version of npm available! 8.19.4
- `package_managers` = `maven` from `[REQ]`: ? github.com/elastic/go-sysinfo/internal/registry [no test files] ? github.com/elastic/go-sysinfo/providers/aix [no test files] ? github.com/elastic/go-sysinfo/providers/shared [no test files] ? github.com/elastic/go-sysinfo/providers/windows [no test files] ?
- `package_managers` = `yarn` from `[REQ]`: Here's the result of running `cat -n` on [PATH]: 1 /** 2 * MIT License 3 * 4 * Copyright (c) 2020-present, Elastic NV 5 * 6 * Permission is hereby granted, free of charge, to any person obtaining a copy 7 * of this software and associated documentation files (
- `build_tools` = `make` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT

## profile_example_2

- Cluster: `hybrid_o_000152`
- Majority owner-like label: `[ORG]`
- Requests: 4

### Fields

- `languages`: `['go', 'python']`
- `frameworks`: `['pytest']`
- `package_managers`: `['npm', 'pip']`
- `build_tools`: `['make', 'pytest']`
- `repo_names`: `['[REPO_NAMES]']`
- `internal_domains`: `['[DOMAIN]', '[DOMAIN]', '[DOMAIN]', '[DOMAIN]', '[DOMAIN]']`

### Evidence

- `frameworks` = `pytest` from `[REQ]`: Here's the result of running `cat -n` on [PATH]: 1 from enum import Enum 2 from random import randint 3 4 import pytest 5 6 from pythonfmu.enums import Fmi2Causality, Fmi2Initial, Fmi2Variability 7 from pythonfmu.variables import Boolean, Integer, Real, Scalar
- `package_managers` = `pip` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `package_managers` = `npm` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `build_tools` = `pytest` from `[REQ]`: Here's the result of running `cat -n` on [PATH]: 1 from enum import Enum 2 from random import randint 3 4 import pytest 5 6 from pythonfmu.enums import Fmi2Causality, Fmi2Initial, Fmi2Variability 7 from pythonfmu.variables import Boolean, Integer, Real, Scalar
- `build_tools` = `make` from `[REQ]`: Let me test some edge cases and additional scenarios to make sure everything works correctly:
- `languages` = `python` from `[REQ]`: Here's the result of running `cat -n` on [PATH]: 1 import math 2 import tempfile 3 from pathlib import Path 4 5 import pytest 6 7 from pythonfmu.builder import FmuBuilder 8 9 pyfmi = pytest.importorskip( 10 "pyfmi", reason="pyfmi is required for testing the pr

## profile_example_3

- Cluster: `hybrid_o_000082`
- Majority owner-like label: `[ORG]`
- Requests: 84

### Fields

- `languages`: `['go', 'java', 'javascript', 'python', 'rust']`
- `package_managers`: `['cargo', 'npm', 'pip']`
- `build_tools`: `['bazel', 'cargo', 'go test', 'make']`
- `repo_names`: `['[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]', '[REPO_NAMES]']`
- `internal_domains`: `['[DOMAIN]']`

### Evidence

- `package_managers` = `pip` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `package_managers` = `npm` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `package_managers` = `cargo` from `[REQ]`: total 84 drwxr-xr-x 14 root root 460 Apr 23 20:21 . drwxr-xr-x 3 root root 80 Apr 23 20:21 .. drwxr-xr-x 9 root root 320 Apr 23 20:21 .git drwxr-xr-x 4 root root 140 Apr 23 20:21 .github -rw-r--r-- 1 root root 16 Apr 23 20:21 .gitignore -rw-r--r-- 1 root root 
- `build_tools` = `make` from `[REQ]`: Here's the result of running `cat -n` on [PATH]: 2355 return result 2356 2357 # TODO: Make canonicalize_shape return named shapes? 2358 def as_named_shape(shape) -> NamedShape: 2359 if isinstance(shape, NamedShape): 2360 return shape 2361 return NamedShape(*sh
- `build_tools` = `bazel` from `[REQ]`: Here's the files and directories up to 2 levels deep in [PATH], excluding hidden items: [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PATH] [PAT
- `build_tools` = `cargo` from `[REQ]`: total 84 drwxr-xr-x 14 root root 460 Apr 23 20:21 . drwxr-xr-x 3 root root 80 Apr 23 20:21 .. drwxr-xr-x 9 root root 320 Apr 23 20:21 .git drwxr-xr-x 4 root root 140 Apr 23 20:21 .github -rw-r--r-- 1 root root 16 Apr 23 20:21 .gitignore -rw-r--r-- 1 root root 
