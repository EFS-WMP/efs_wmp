# CI Docker Gate Documentation

> This repo has no CI runner configured yet. This document serves as a runbook for implementing the CI pipeline.

---

## Overview

Run Odoo tests in Docker container as a CI gate before merge.

---

## Job Steps

1. **Checkout code** 
2. **Start PostgreSQL** (`db18` service)
3. **Wait for DB ready**
4. **Run tests** (one-shot with `run --rm`)
5. **Capture test log as artifact**
6. **Fail on test failures**

---

## GitHub Actions Skeleton

```yaml
# .github/workflows/odoo-tests.yml
name: Odoo itad_core Tests

on:
  pull_request:
    paths:
      - 'addons/common/itad_core/**'
  push:
    branches: [main]
    paths:
      - 'addons/common/itad_core/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Start PostgreSQL
        run: |
          docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d db18
          # Wait for postgres to be ready
          sleep 10

      - name: Run itad_core tests
        run: |
          docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18 \
            odoo --test-enable --test-tags=itad_core \
            -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core \
            --stop-after-init --no-http --http-port=0 \
            2>&1 | tee artifacts/odoo_itad_core_tests.log

      - name: Check for test failures
        run: |
          if grep -E "(FAIL|ERROR):" artifacts/odoo_itad_core_tests.log; then
            echo "Tests failed!"
            exit 1
          fi

      - name: Upload test log
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: odoo-test-log
          path: artifacts/odoo_itad_core_tests.log
          retention-days: 30

      - name: Cleanup
        if: always()
        run: |
          docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml down -v
```

---

## GitLab CI Skeleton

```yaml
# .gitlab-ci.yml
stages:
  - test

odoo-tests:
  stage: test
  image: docker:24
  services:
    - docker:dind
  variables:
    DOCKER_HOST: tcp://docker:2375
  before_script:
    - apk add --no-cache docker-compose
  script:
    - docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml up -d db18
    - sleep 10
    - docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml run --rm -T odoo18
        odoo --test-enable --test-tags=itad_core
        -c /etc/odoo/odoo.conf -d odoo18_db -u itad_core
        --stop-after-init --no-http --http-port=0
        2>&1 | tee artifacts/odoo_itad_core_tests.log
  after_script:
    - docker compose -p odoo18 -f docker/odoo18/docker-compose.odoo18.yml down -v
  artifacts:
    paths:
      - artifacts/odoo_itad_core_tests.log
    when: always
    expire_in: 30 days
  only:
    changes:
      - addons/common/itad_core/**
```

---

## Artifact Storage

| Artifact | Path | Retention |
|----------|------|-----------|
| Test log | `artifacts/odoo_itad_core_tests.log` | 30 days |

---

## Expected Test Output

Success:
```
Ran X tests in Y.YYYs
OK
```

Failure (gate should fail):
```
FAIL: test_something
ERROR: test_other
```
