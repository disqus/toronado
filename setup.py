#!/usr/bin/env python

from setuptools import find_packages, setup


install_requires = [
    'cssselect',
    'cssutils',
    'lxml',
]

tests_require = [
    'exam',
    'pytest',
]

setup(
    name='toronado',
    version='0.0.11',
    description='Fast lxml-based CSS stylesheet inliner.',
    author='ted kaemming, disqus',
    author_email='ted@disqus.com',
    packages=find_packages(exclude=('tests',)),
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'dev': [
            'flake8',
        ],
        'tests': tests_require,
    },
    zip_safe=False,
    license='Apache License 2.0',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)
