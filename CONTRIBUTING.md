# Contributing to halo

First off, thank you for considering contributing to halo! It's people like you that make halo such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by the [halo Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for halo. Following these guidelines helps maintainers and contributors understand your report, reproduce the behavior, and find related reports.

Before creating bug reports, please check this list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible.

- **Check if your terminal supports True Color.** halo requires a terminal that supports 24-bit color.
- **Check your Python version.** halo requires Python 3.10 or later.
- **Check the Issues page** to see if the bug has already been reported.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for halo, including completely new features and minor improvements to existing functionality.

- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
- **Explain why this enhancement would be useful** to most halo users.

### Your First Code Contribution

Unsure where to begin contributing to halo? You can start by looking through these `good first issue` and `help wanted` issues:

- `good first issue` - issues which should only require a few lines of code, and a test or two.
- `help wanted` - issues which should be a bit more involved than `good first issue` issues.

#### Local Development

1. Fork the repo and clone it locally.
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Linux/macOS: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
4. Install dependencies: `pip install -e .`
5. Run the project: `halo`

### Styleguides

#### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

#### Python Styleguide

- Use [ruff](https://github.com/astral-sh/ruff) for linting and formatting.
- Follow PEP 8 guidelines.
- Use type hints for all function signatures.
- Ensure all tests pass before submitting a pull request.

## Pull Requests

- Fill in the required template.
- Do not include any changes that are not related to the issue.
- Ensure that the CI/CD pipeline passes.
- After a pull request is merged, you can safely delete your branch.
