set dotenv-load

@_default:
    just --list

bootstrap:
    @just lock
    uv pip sync requirements.txt

install:
    rye tools uninstall git-scripts
    rye tools install git-scripts --path . --force

lock: venv
    uv pip compile pyproject.toml --output-file requirements.txt

venv:
    uv venv
