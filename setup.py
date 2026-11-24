#!/usr/bin/env python
# coding=utf-8

from pathlib import Path
from setuptools import setup, find_packages

setup(
    name='norfetool',
    version="1.6.0",
    description="Scientific plotting, bibliography cleaning and LaTeX document builds",
    long_description=(Path(__file__).parent / "readme.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    python_requires=">=3.9",
    # long_description=open('README.rst').read(),
    author='norfe',
    author_email='21121598@bjtu.edu.cn',
    maintainer='norfe',
    maintainer_email='21121598@bjtu.edu.cn',
    license='BSD License',
    packages=find_packages(include=["norfetools", "norfetools.*"]),
    # py_modules=["norfetools"],
    platforms=["all"],
    url='https://github.com/liftes/PythonDraw',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries'
    ],
    install_requires=[
        'matplotlib',
        'numpy',
    ]
)
# Build: python -m build
# Upload only the two artifacts for the intended release with python -m twine upload.

# python setup.py sdist
# twine upload -u __token__ -p pypi-token dist/*