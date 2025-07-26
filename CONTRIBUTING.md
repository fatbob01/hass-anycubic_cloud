# Contributing

Thank you for considering a contribution!

## Commit messages

Use a short imperative sentence that summarises the change. Examples:

```
Fix tab retrieval for page selection
Update login prompt on authentication page
```

Keeping commit messages concise helps reviewers understand the purpose of each change.

## Development

Install the pre-commit hooks and run them before submitting a pull request:

```bash
pip install pre-commit
pre-commit install
pre-commit run --files <changed files>
```

Pull requests should target the `work` branch.
