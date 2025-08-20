# PyPI Publishing Setup Guide

This guide explains how to set up automatic PyPI publishing for Reticulum.

## 🔑 Required Secrets

### 1. PyPI API Token

1. **Create PyPI Account**: [Register at PyPI](https://pypi.org/account/register/)
2. **Generate API Token**: 
   - Go to Account Settings → API tokens
   - Click "Add API token"
   - Select "Entire account (all projects)"
   - Copy the token (starts with `pypi-`)

### 2. Add GitHub Secret

1. Go to your GitHub repository: `https://github.com/plexicus/reticulum`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. **Name**: `PYPI_API_TOKEN`
5. **Value**: Paste your PyPI API token
6. Click **Add secret**

## 🚀 Publishing Process

### Automatic Publishing (Recommended)

The GitHub Action automatically publishes when you:

1. **Create a Git Tag**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **The Action Will**:
   - Run tests on multiple Python versions
   - Build the package
   - Publish to PyPI
   - Create a GitHub release

### Manual Publishing

```bash
# Build the package
poetry build

# Publish to PyPI (requires PyPI credentials)
poetry publish
```

## 📦 Package Information

- **Package Name**: `reticulum`
- **Install Command**: `pip install reticulum`
- **Import**: `from reticulum import ExposureScanner`

## 🔄 Version Management

Update version in `pyproject.toml`:

```toml
[tool.poetry]
version = "0.1.1"  # Increment this for each release
```

Then create and push a new tag:

```bash
git add pyproject.toml
git commit -m "bump version to 0.1.1"
git tag v0.1.1
git push origin main
git push origin v0.1.1
```

## ✅ Verification

After publishing, verify at:
- [PyPI Package Page](https://pypi.org/project/reticulum/)
- [Test Installation](https://pypi.org/project/reticulum/#installation)

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication Failed**: Check `PYPI_API_TOKEN` secret
2. **Version Already Exists**: Increment version in `pyproject.toml`
3. **Build Failed**: Check Poetry configuration and dependencies

### Support

- [PyPI Help](https://pypi.org/help/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
