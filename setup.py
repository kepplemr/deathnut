from setuptools import find_packages, setup

setup(
    name="deathnut",
    version="0.1",
    description="Simple redis-based authorization library",
    install_requires=["redis==3.3.11"],
    packages=find_packages(),
    test_suite="nose.collector",
)
