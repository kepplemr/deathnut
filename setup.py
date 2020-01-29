from setuptools import setup

setup(
    name="deathnut",
    version="0.1",
    description="Simple redis-based authorization library",
    install_requires=["redis==3.3.11"],
    packages=["deathnut"],
    test_suite="nose.collector",
)
