"""
Setup script for ops-cli.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="ops-cli",
    version="0.1.0",
    description="OPS Admin Platform Project Manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Edison",
    author_email="edison@example.com",
    url="https://github.com/edisonlil/ops-admin-platform",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # No external dependencies for core functionality
    ],
    entry_points={
        "console_scripts": [
            "ops-cli=ops_cli.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
    ],
    python_requires=">=3.8",
)