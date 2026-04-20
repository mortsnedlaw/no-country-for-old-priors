# Contributing to no-country-for-old-priors

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/no-country-for-old-priors.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
5. Install dev dependencies: `pip install -e ".[dev]"`

## Development Workflow

### Code Style
- Follow PEP 8
- Use type hints where possible
- Format with `black`:
  ```bash
  black no_country_for_old_priors/ tests/
  ```

### Testing
- Add tests for new features
- Run tests: `pytest tests/`
- Check coverage: `pytest --cov=no_country_for_old_priors tests/`

### Documentation
- Update README.md for user-facing changes
- Update ARCHITECTURE.md for design changes
- Add docstrings to all functions
- Include examples where helpful

## Areas for Contribution

### High Priority
- [ ] Add comprehensive test suite
- [ ] Support for additional log formats (Splunk, ELK, etc.)
- [ ] Performance optimization for large log files
- [ ] Additional DICOM query options
- [ ] Database query optimization

### Medium Priority
- [ ] REST API for remote analysis
- [ ] Web UI for report viewing
- [ ] Email report delivery
- [ ] Support for other DICOM operations (C-MOVE with restrictions)
- [ ] Machine learning for anomaly detection

### Lower Priority
- [ ] Internationalization support
- [ ] Plugin system for custom analysis
- [ ] Integration with EHR systems
- [ ] Advanced visualization tools

## Reporting Issues

When reporting issues, please include:
1. Python version: `python --version`
2. Package versions: `pip list | grep -E "(pydicom|pynetdicom|click|pandas)"`
3. Operating system
4. Steps to reproduce
5. Error message and traceback
6. Sample log files (anonymized)

## Pull Request Process

1. Update the README.md with any new features or changes
2. Update ARCHITECTURE.md if design changes are significant
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Format code: `black no_country_for_old_priors/`
6. Lint code: `flake8 no_country_for_old_priors/`
7. Create descriptive pull request with:
   - What changes were made
   - Why they were needed
   - How to test them

## Code Review Checklist

When reviewing PRs, check:
- [ ] Code follows PEP 8 style
- [ ] Type hints are present
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] Docstrings are clear
- [ ] Error handling is appropriate
- [ ] Performance impact is acceptable
- [ ] No security vulnerabilities introduced

## Release Process

1. Update version in `__init__.py` and `setup.py`
2. Update CHANGELOG (when implemented)
3. Tag release: `git tag -a v0.1.0 -m "Release version 0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. Build package: `python setup.py sdist bdist_wheel`
6. Upload to PyPI: `twine upload dist/*`

## Questions?

- Check existing issues and discussions
- Review ARCHITECTURE.md for design decisions
- Look at examples.py for usage patterns
- Check test suite for implementation examples

Thank you for contributing!
