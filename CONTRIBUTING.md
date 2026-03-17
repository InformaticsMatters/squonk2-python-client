# Contributing
The project uses: -

- [pre-commit] to enforce linting of files prior to committing them to the
  repository
- [Commitizen] to enforce a [Convention Commit] commit message format
- [ruff] as a code linter and formatter
- [uv] for project management

You **MUST** comply with these choices in order to  contribute to the project.

To get started review the pre-commit utility and the conventional commit style
and then set-up your local clone by following the **Installation** and
**Quick Start** sections: -

    uv venv
    uv sync --group dev
    uv run pre-commit install -t commit-msg -t pre-commit

Now the project's rules will run on every commit, and you can check the
current health of your clone with: -

    uv run pre-commit run --all-files

## Local Development
You can build and install the package locally using the same process used
by the GitHib Actions: -

    rm -rf dist/*
    uv build
    pip install dist/im_squonk2_client-*.tar.gz

And then uninstall using pip: -

    pip uninstall im-squonk2-client -y

With a suitable Squonk installation you should be able to run the basic test module,
which exercises a number of API methods. You will need to define a number of variables,
but one done the test is expected to work: -

    export SQUONK2_DMAPI_URL=https://data-manager-test.example.com/data-manager-api
    export SQUONK2_KEYCLOAK_URL=https://keycloak-test.example.com/auth
    export SQUONK2_KEYCLOAK_REALM=squonk
    export SQUONK2_KEYCLOAK_DM_CLIENT_ID=data-manager-api-test
    export SQUONK2_KEYCLOAK_USER=dmit-user-admin
    export SQUONK2_KEYCLOAK_USER_PASSWORD=password1234

    uv run test.py

Feel free to extend the test module as you add API methods.

---

[ruff]: https://docs.astral.sh/ruff
[commitizen]: https://commitizen-tools.github.io/commitizen/
[conventional commit]: https://www.conventionalcommits.org/en/v1.0.0/
[pre-commit]: https://pre-commit.com
[uv]: https://docs.astral.sh/uv/
