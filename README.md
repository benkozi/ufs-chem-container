# ufs-chem-container

Base container recipes and automated build infrastructure for UFS Chemistry (UFS-Chem).

## Overview & Purpose

`ufs-chem-container` provides the authoritative, decoupled base environment container images used across the UFS Chemistry ecosystem, including [CATChem](https://github.com/ufs-community/CATChem). Container image recipes and build workflows are extracted and decoupled from individual modeling repositories to centralize base environment maintenance, reduce redundant builds, and ensure cross-platform reproducibility.

## Drop-in Compatibility with CATChem

The container images built by this repository provide an exact, 100% drop-in replacement for CATChem's legacy Spack base image:
- **Base OS**: Ubuntu 24.04 LTS
- **System Dependencies**: Full compiler and library suite (`build-essential`, `gfortran`, `cmake`, `libopenmpi-dev`, `libnetcdf-dev`, `libnetcdff-dev`, `liblapack-dev`, `libopenblas-dev`, `cython3`, etc.)
- **Rust Toolchain**: Stable Rust installed via rustup
- **Spack-Stack**: Cloned from [JCSDA/spack-stack](https://github.com/JCSDA/spack-stack) at commit `37c009d` (v2.1.1)
- **Spack Environment (`ufschem`)**: Concretized and installed with `esmf` (against system OpenMPI), `yaml-cpp`, `parallelio+pnetcdf`, and `py-pip`
- **Default Shell**: Automatically sources `/opt/ufschem/spack-stack/setup.sh` and activates the `ufschem` Spack environment

## Image Variants & Naming Conventions

Images are hosted on Docker Hub under the [noaaepic](https://hub.docker.com/u/noaaepic) organization at [noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev](https://hub.docker.com/repository/docker/noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev/general). The organization namespace is configured via repository secret `DOCKER_ORG`:

| Branch / Context | Image Name | Tags | Purpose |
|---|---|---|---|
| `main` | `ufschem-spack-base-ubuntu-gcc-13` | `<version>` (e.g. `0.1.0`), `latest` | Stable production base image |
| `develop` | `ufschem-spack-base-ubuntu-gcc-13-dev` | `<version>-rc.X` (e.g. `0.1.0-rc.1`) | Prerelease release candidate |
| PR with `sandbox-build` | `ufschem-spack-base-ubuntu-gcc-13-sandbox` | `<sandbox-version>` (e.g. `7.7.7-rc.1`) | Temporary sandbox image for external application testing prior to merge |

> **Note**: Prerelease builds on `develop` never update the `:latest` tag on Docker Hub.

### Pulling Pre-built Images from Docker Hub

To pull pre-built images for downstream modeling or integration testing:

- **Production release**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13:latest
  # or specific version:
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13:0.1.0
  ```

- **Prerelease candidate**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13-dev:0.1.0-rc.1
  ```

- **Sandbox test build**:
  ```bash
  docker pull noaaepic/ufschem-spack-base-ubuntu-gcc-13-sandbox:7.7.7-rc.1
  ```


## Sandbox Builds for Testing and Development

Recipe changes may need to be tested by an external application (such as downstream modeling workflows or CATChem integration suites) before merging into `develop`. Pull requests can trigger temporary sandbox builds published to Docker Hub:

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


## Building Locally

To build the Spack base container image locally using Docker Buildx:

```bash
docker buildx build -f docker/Dockerfile.ufschem-spack-base-ubuntu-gcc-13 -t ufschem-spack-base:local .
```

To run the container interactively and verify the Spack environment:

```bash
docker run -it --rm ufschem-spack-base:local bash
```

Inside the container:

```bash
spack env status
spack find
```

## Repository Configuration & Secrets

The GitHub Actions workflows require the following repository-level secrets when publishing images (all Docker configuration is managed via repository secrets with no defaults):

- **Repository Secrets**:
  - `DOCKER_ORG`: Docker Hub organization / namespace (`noaaepic`).
  - `DOCKER_USERNAME`: Docker Hub account username with write permissions to `noaaepic`.
  - `DOCKERHUB_TOKEN`: Docker Hub Personal Access Token (PAT) with read/write permissions for `noaaepic`.
  - `SEMVER_APP_ID`: GitHub App Client ID (or App ID) for automated semantic release.
  - `SEMVER_APP_PRIVATE_KEY`: GitHub App private key (`.pem`) for automated semantic release and branch protection bypass.

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
