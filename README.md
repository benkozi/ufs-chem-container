# ufs-chem-container

Base container recipes and automated build infrastructure for UFS Chemistry (UFS-Chem).

## Overview & Purpose

`ufs-chem-container` provides the authoritative, decoupled base environment container images used across the Unified Forecast System (UFS) Chemistry ecosystem. Container recipes and automated build workflows are maintained centrally to ensure cross-platform reproducibility, streamline dependency management, and eliminate redundant Spack build pipelines across downstream atmospheric and chemistry modeling workflows.

## Supported Container Images & Dockerfiles

This repository maintains modular Dockerfiles under [`docker/`](docker/) to generate standardized base environments for UFS Chemistry applications.

### `ufschem-spack-base-ubuntu-gcc-13`

- **Dockerfile**: [`docker/Dockerfile.ufschem-spack-base-ubuntu-gcc-13`](docker/Dockerfile.ufschem-spack-base-ubuntu-gcc-13)
- **Target Scope**: `spack-base`
- **Base OS**: Ubuntu 24.04 LTS (`noble`)
- **Architecture**: `linux/amd64`
- **Compiler**: GCC 13 (`build-essential`, `gfortran`)

#### Environment & Installed Packages

- **System Toolchain & Build Utilities**:
  - Compilers & build tools: `build-essential`, `gfortran`, `cmake`, `ninja-build`
  - Communications & Parallel I/O: OpenMPI (`libopenmpi-dev`), NetCDF-C (`libnetcdf-dev`), NetCDF-Fortran (`libnetcdff-dev`), Lapack (`liblapack-dev`), OpenBLAS (`libopenblas-dev`)
  - Interpreters & Runtimes: Python 3.12 (`python3-dev`, `python3-venv`, `python3-pip`, `cython3`), Rust (stable toolchain installed via rustup in `/usr/local/rustup` and `/usr/local/cargo`)
  - Scientific & Utility Libraries: `nco`, `libxml2`, `libxml2-dev`, `libxml2-utils`, `libcurl4-openssl-dev`, `gettext`, `tmux`, `less`, `vim`, `git`, `tar`
- **Spack-Stack Integration**:
  - Cloned from [JCSDA/spack-stack](https://github.com/JCSDA/spack-stack) at commit `37c009d` (release v2.1.1) into `/opt/ufschem/spack-stack`.
  - External system packages registered: `rust`, `curl`, `perl`, `git`, `python`, `py-cython`, `cmake`, `gettext`, `findutils`, `tar`, `libxml2`, `openssl`, `openmpi`.
- **Pre-Concretized Spack Environment (`ufschem`)**:
  - `esmf` (linked against system OpenMPI `^openmpi`)
  - `yaml-cpp`
  - `parallelio+pnetcdf`
  - `py-pip`
  - Fully concretized, built with `--fail-fast`, garbage-collected, and package cache cleaned.
- **Runtime Environment & Activation**:
  - Default shell: `/bin/bash`
  - Default working directory: `/opt`
  - Automatic activation: `~/.bashrc` automatically sources `/opt/ufschem/spack-stack/setup.sh` and executes `spack env activate ufschem`.

#### Local Build & Interactive Usage

To build the image locally with Docker Buildx:

```bash
docker buildx build -f docker/Dockerfile.ufschem-spack-base-ubuntu-gcc-13 -t ufschem-spack-base-ubuntu-gcc-13:local .
```

To run the container interactively and verify the Spack environment:

```bash
docker run -it --rm ufschem-spack-base-ubuntu-gcc-13:local bash
```

Inside the container:

```bash
spack env status
spack find
```

## Image Variants & Naming Conventions

Images are hosted on Docker Hub under the [noaaepic](https://hub.docker.com/u/noaaepic) organization at [noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev](https://hub.docker.com/repository/docker/noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev/general). The organization namespace is configured via repository secret `DOCKER_ORG`:

| Branch / Context | Image Name | Tags | Purpose |
|---|---|---|---|
| `main` | `ufschem-spack-base-ubuntu-gcc-13` | `<version>` (e.g. `0.2.0`), `latest` | Stable production base image |
| `develop` | `ufschem-spack-base-ubuntu-gcc-13-dev` | `<version>-rc.X` (e.g. `0.2.0-rc.2`), `latest` | Prerelease release candidate |
| PR with `sandbox-build` | `ufschem-spack-base-ubuntu-gcc-13-sandbox` | `<sandbox-version>` (e.g. `7.7.7-rc.1`) | Temporary sandbox image for external application testing prior to merge |

> **Note**: Prerelease builds on `develop` update the `:latest` tag on the `-dev` repository (`<image>-dev:latest`). Production builds on `main` update `:latest` on the production repository. Sandbox builds on PRs omit the `:latest` tag to prevent collisions across concurrent pull requests.

### Pulling Pre-built Images from Docker Hub

To pull pre-built images for downstream modeling or integration testing:

- **Production release**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13:latest
  # or specific version:
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13:0.2.0
  ```

- **Prerelease candidate**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev:0.2.0-rc.2
  ```

- **Sandbox test build**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13-sandbox:7.7.7-rc.1
  ```

## Sandbox Builds for Testing and Development

Recipe changes may need to be tested by an external application (such as downstream UFS modeling workflows or integration test suites) before merging into `develop`. Pull requests can trigger temporary sandbox builds published to Docker Hub:

### Triggering a Sandbox Build
1. **Apply Label**: Add the `sandbox-build` label to the Pull Request.
2. **Specify Version Tag**: Include `sandbox-version=<version>` on its own line in the Pull Request description (body). For example:
   ```markdown
   sandbox-version=7.7.7-rc.1
   ```

### Behavior & Constraints
- **Validation**: If a PR is labeled with `sandbox-build` but does not include a valid `sandbox-version=` on its own line in the PR description, the CI workflow will raise an error and abort immediately.
- **Repository Destination & Caching**: The image is published strictly to `${DOCKER_ORG}/<image-name>-sandbox:<sandbox-version>`. Sandbox builds do not push a `:latest` tag to eliminate collisions across concurrent pull requests; subsequent builds on the same PR reuse layer cache directly from `<image-name>-sandbox:<sandbox-version>`.
- **Branch Isolation**: Sandbox images are **never** built or pushed on `develop` or `main` branches. They exist solely for pre-merge testing during PR review.
- **Pulling the Sandbox Image**: External applications can pull and execute the sandbox image using:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13-sandbox:7.7.7-rc.1
  ```

## Repository Configuration & Secrets

The GitHub Actions workflows require the following repository-level secrets when publishing images (all Docker configuration is managed via repository secrets with no defaults):

- **Repository Secrets**:
  - `DOCKER_ORG`: Docker Hub organization / namespace (`noaaepic`).
  - `DOCKER_USERNAME`: Docker Hub account username with write permissions to `noaaepic`.
  - `DOCKERHUB_TOKEN`: Docker Hub Personal Access Token (PAT) with read/write permissions for `noaaepic`.
  - `SEMVER_APP_ID`: GitHub App Client ID (or App ID) for automated semantic release. Requires branch ruleset bypass permissions (`bypass_actors`) for protected branches (`develop`, `main`).
  - `SEMVER_APP_PRIVATE_KEY`: GitHub App private key (`.pem`) for automated semantic release and branch protection bypass.

### Fork Pull Requests & Security Context

Pull requests originating from external forks run in GitHub's restricted security context where repository secrets are withheld:
- **Local Container Build Verification**: The `build-test` job runs cleanly on fork PRs, building with Docker Buildx and verifying local registry push (`localhost:5000`) with public layer cache fallbacks. Docker Hub credential verification is gracefully skipped.
- **Semantic Release Preview**: The preview workflow evaluates the PR title and generates projected release diffs using `github.token` fallback, gracefully skipping App token verification.
- **Sandbox Builds**: Publishing sandbox test containers to Docker Hub requires write secrets and must be triggered from internal branches within `ufs-community/ufs-chem-container`.

### Automated Secret & Permission Verification

A dedicated verification workflow ([.github/workflows/verify-secrets.yml](.github/workflows/verify-secrets.yml)) runs on a daily cron schedule (`0 6 * * *` at 06:00 UTC) and can be triggered on demand via `workflow_dispatch`. It continuously verifies:
1. Docker Hub login and registry push permissions for all target repositories (`ufschem-spack-base-ubuntu-gcc-13`, `ufschem-spack-base-ubuntu-gcc-13-dev`, and `ufschem-spack-base-ubuntu-gcc-13-sandbox`).
2. GitHub App token acquisition, repository write permissions, Git ref operations, and branch ruleset bypass permissions on `develop` and `main`.


## Development & Pre-Commit

This repository uses [pre-commit](https://pre-commit.com/) orchestrated through [uv](https://docs.astral.sh/uv/) for code hygiene, formatting, type checking, and conventional commit message validation.

### Setup

```bash
uv sync --all-groups
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

### Running Manually

```bash
uv run pre-commit run --all-files
```

The pre-commit hooks include:
- `conventional-pre-commit`: Enforces Conventional Commit grammar on commit messages.
- `trailing-whitespace` & `end-of-file-fixer`: General file hygiene.
- `check-toml`: Syntax validation for `pyproject.toml`.
- `ruff` (linter & formatter): Python code quality.
- `mypy`: Static type analysis.
- `yamlfix` & `yamllint`: YAML style and syntax checking.

## Release Process & Conventional Commits

Releases are fully automated via `python-semantic-release` (PSR) v10:
- Commits and PR titles must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
  - `feat: ...` → bumps minor version (e.g., `0.1.0` → `0.2.0`).
  - `fix: ...` → bumps patch version (e.g., `0.1.0` → `0.1.1`).
  - `chore: ...`, `docs: ...`, `refactor: ...` → no version bump unless breaking change specified.
  - `feat!: ...` or `BREAKING CHANGE:` → bumps major version.
- Merges into `develop` publish prerelease versions (`0.1.0-rc.X`) and push dev candidate container images.
- Merges into `main` publish formal releases (`0.1.0`), tag the Git commit, update `CHANGELOG.md`, and push production images tagged with the release version and `latest`.
