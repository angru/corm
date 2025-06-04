import os

from setuptools import setup


def open_file(filename):
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        mode="r",
        encoding="utf-8",
    ) as f:
        return f.read()


setup(
    name="corm",
    version="0.0.3",
    description="Relationships between data structures",
    long_description=open_file("README.md"),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Environment :: MacOS X",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
    ],
    author="Andrey Shevchuk",
    author_email="angru@list.ru",
    url="https://github.com/angru/corm",
    license="MIT",
    packages=["corm"],
    python_requires=">=3.9",
)
