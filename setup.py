from setuptools import setup, find_packages

setup(
    name="sparc-generator",
    version="0.1.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "openai>=0.27.8",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "tiktoken>=0.4.0",
        "click>=8.1.3",
        "scholarly>=1.0.0",
        "numpy>=1.23.5",
        "pandas>=2.0.3",
        "torch>=2.0.0",
        "matplotlib>=3.7.2",
    ],
    entry_points={
        "console_scripts": [
            "sparc=sparc_generator.sparc_cli:cli",
        ],
    },
    package_data={
        'sparc_generator': ['sparc_prompts.yaml'],
    },
    python_requires=">=3.9",
    author="FrancyJGLisboa",
    author_email="francy@example.com",  # Add your email here
    description="Convert YouTube transcripts and academic papers into SPARC development artifacts.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/FrancyJGLisboa/Youtube-Transcript-to-SPARC-FRAMEWORK",
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
)
