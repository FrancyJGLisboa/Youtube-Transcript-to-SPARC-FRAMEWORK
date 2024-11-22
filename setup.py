"""Setup script for SPARC Framework Generator."""
from setuptools import setup, find_packages

setup(
    name="sparc-generator",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
        "openai==0.28",
        "rich",
        "pyyaml",
        "python-dotenv",
        "asyncio",
    ],
    entry_points={
        "console_scripts": [
            "sparc=sparc_generator.sparc_cli:cli",
        ],
    },
    python_requires=">=3.8",
    package_data={
        "sparc_generator": ["sparc_prompts.yaml"],
    },
)
