# 🙌 Contributing to HackRadar

Thank you for showing interest in contributing to **HackRadar**! We welcome all kinds of contributions — bug fixes, new scrapers, feature requests, or improvements to the documentation.


## 🛠️ How to Contribute

1. **Fork the repo** and clone your fork locally.
2. Create a new branch:

   ```bash
   git checkout -b your-feature-name
   ```
3. Make your changes.
4. Run the tests and ensure everything works (see below).
5. Commit and push your changes:

   ```bash
   git commit -m "Add your message here"
   git push origin your-feature-name
   ```
6. Open a Pull Request.


## ✅ Guidelines

* Follow existing code structure and naming conventions.
* Keep your changes focused and minimal.
* Write clear and concise commit messages.
* If adding a new scraper, place it in the `adapters/` folder.

## 🧪 Running Tests (pytest)

We use `pytest` for testing. Before opening a PR, run:

```bash
uv run pytest
```

Make sure all tests pass and add tests for any new functionality where appropriate.

## 🧹 Pre-commit Hooks

This repo uses `pre-commit` to enforce formatting and basic quality checks.

1. Install hooks (one-time):

```bash
uv run pre-commit install
```

2. Run hooks locally (optional but recommended before pushing):

```bash
uv run pre-commit run --all-files
```

CI will run these checks as well, so keeping them green locally will make your PR review smoother.


## 📞 Need Help?

Feel free to open an issue or discussion if you have any questions.

We’re glad to have you here 💙
