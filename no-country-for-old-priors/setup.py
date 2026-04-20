from setuptools import setup, find_packages

setup(
    name="no-country-for-old-priors",
    version="0.1.0",
    description="Analyze PACS logs to identify ad-hoc retrieve events and correlate with DICOM metadata",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Healthcare Analytics",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "pydicom>=2.4.0",
        "pandas>=2.0.0",
        "jinja2>=3.1.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "dicom": [
            "pynetdicom>=1.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "no-country-for-old-priors=no_country_for_old_priors.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    keywords="PACS DICOM healthcare radiology prefetch",
    url="https://github.com/yourusername/no-country-for-old-priors",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/no-country-for-old-priors/issues",
        "Source": "https://github.com/yourusername/no-country-for-old-priors",
    },
)
