# Contributing to ITBench-Scenarios

ITBench-Scenarios accepts contributions through GitHub pull request.

## Required Software

- [Python3](https://www.python.org/downloads/) (v3.12.z)

## Environment Set Up Guide

1. Create a Python virtual environment.

```shell
python -m venv venv
```

2. Install the Python dependencies

```shell
python -m pip install -r requirements-dev.txt
```

3. Install `pre-commit` to the repo. This only needs to be done once.

```shell
pre-commit install
pre-commit install --hook-type commit-msg --hook-type pre-push
```

## Committing Code

This projects requires the use of [pre-commit](https://github.com/pre-commit/pre-commit), [detect-secrets](https://github.com/Yelp/detect-secrets), and [commitizen](https://github.com/commitizen-tools/commitizen). These tools are installed through the process mentioned [here](#environment-set-up-guide).

All commits submitted to this repository must be signed, pass the pre-commit tests, and formatted through commitizen.

In order to sign and commit code using commitizen, please run the following command after staging changes via `git add`:

```shell
cz commit -- --signoff
```
