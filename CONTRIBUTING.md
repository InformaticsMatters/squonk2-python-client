# Contributing
The project uses: -

- [pre-commit] to enforce linting of files prior to committing them to the
  repository
- [Commitizen] to enforce a [Convention Commit] commit message format
- [Black] as a code formatter

You **MUST** comply with these choices in order to  contribute to the project.

To get started review the pre-commit utility and the conventional commit style
and then set-up your local clone by following the **Installation** and
**Quick Start** sections: -

    pip install --upgrade pip
    pip install -r build-requirements.txt
    pre-commit install -t commit-msg -t pre-commit

Now the project's rules will run on every commit, and you can check the
current health of your clone with: -

    pre-commit run --all-files

## Local Development
You can build and install the package locally using the same process used
by the GitHib Actions: -

    pip install build
    rm -rf /dist/*
    python -m build --sdist --wheel --outdir dist/
    pip install dist/im-squonk2-client-*.tar.gz

And then uninstall using pip: -

    pip uninstall im-squonk2-client

---

[black]: https://black.readthedocs.io/en/stable
[commitizen]: https://commitizen-tools.github.io/commitizen/
[conventional commit]: https://www.conventionalcommits.org/en/v1.0.0/
[pre-commit]: https://pre-commit.com
