#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names), encoding=kwargs.get("encoding", "utf8")
    ) as fh:
        return fh.read()


EXTRAS_REQUIRE = dict(
    ta=["TA-Lib"],
    io=["tables", "zarr", "openpyxl", "xlwt"],
    compiled=["numba>0.55.0"],
    plotting=["bokeh>3.0.0"],
    apps=["streamlit>1.15.0"],
    test=["pytest", "pytest-watch", "ruff"],
)


setup(
    name="fastbt",
    version="0.4.0",
    license="MIT license",
    description="A simple framework for fast and dirty backtesting",
    long_description="%s\n%s"
    % (
        re.compile("^.. start-badges.*^.. end-badges", re.M | re.S).sub(
            "", read("README.md")
        ),
        re.sub(":[a-z]+:`~?(.*?)`", r"``\1``", read("CHANGELOG.rst")),
    ),
    long_description_content_type="text/markdown",
    author="UM",
    author_email="uberdeveloper001@gmail.com",
    url="https://github.com/uberdeveloper/fastbt",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        # uncomment if you test on these interpreters:
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: Stackless',
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
        "fastbt",
        "backtesting",
        "algorithmic trading",
        "quantitative finance",
        "research",
        "finance",
    ],
    install_requires=[
        # eg: 'aspectlib==1.1.1', 'six>=1.7',
        "pandas>=1.0.0",
        "sqlalchemy<=2.0.0",
        "pendulum>=2.0.0",
    ],
    extras_require=EXTRAS_REQUIRE,
)
