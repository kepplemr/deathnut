from setuptools import find_packages, setup

setup(
    name="deathnut",
    version="1.0",
    description="Simple redis-based authorization library",
    install_requires=["redis==3.3.11"],
    packages=find_packages(),
    include_package_data=True,
    test_suite="nose.collector",
)
