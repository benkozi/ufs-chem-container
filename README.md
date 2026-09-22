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

Images are hosted on Docker Hub at [bkrlps/ufschem-spack-base-ubuntu-gcc-13-dev](https://hub.docker.com/repository/docker/bkrlps/ufschem-spack-base-ubuntu-gcc-13-dev/general). The default organization namespace is `bkrlps` (configurable via repository variable `DOCKER_ORG`):

| Branch | Image Name | Tags | Purpose |
|---|---|---|---|
| `main` | `ufschem-spack-base-ubuntu-gcc-13` | `<version>` (e.g. `0.1.0`), `latest` | Stable production base image |
| `develop` | `ufschem-spack-base-ubuntu-gcc-13-dev` | `<version>-rc.X` (e.g. `0.1.0-rc.1`) | Prerelease release candidate |

> **Note**: Prerelease builds on `develop` never update the `:latest` tag on Docker Hub.

## Building Locally

To build the Spack base container image locally using Docker Buildx:

```bash
docker buildx build -f docker/Dockerfile-Spack-Base -t ufschem-spack-base:local .
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

The GitHub Actions workflows require the following repository configuration when publishing images:

- **Repository Variables**:
  - `DOCKER_ORG`: Docker Hub organization / user namespace (defaults to `bkrlps` if unset).
- **Repository Secrets**:
  - `DOCKER_USERNAME`: Docker Hub account username.
  - `DOCKERHUB_TOKEN`: Docker Hub Personal Access Token (PAT) with read/write permissions.
  - `SEMVER_APP_ID` & `SEMVER_APP_PRIVATE_KEY`: (Optional) GitHub App credentials for automated releases and bypass permissions; defaults to `GITHUB_TOKEN` if omitted.

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
