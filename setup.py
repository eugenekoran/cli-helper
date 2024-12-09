from setuptools import setup, find_packages

setup(
    name="cli-helper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai",
        "rich-click",
        "rich",
    ],
    entry_points={
        "console_scripts": [
            "cli-helper=cli_helper.main:main",
        ],
    },
    author="Eugene Koran",
    author_email="yauheni.koran@gmail.com",
    description="An LLM-powered CLI helper that suggests and executes shell commands",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/eugenekoran/cli-helper",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)