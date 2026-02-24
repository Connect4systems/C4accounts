from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = [line for line in f.read().strip().split("\n") if line]

setup(
    name="c4accounts",
    version="0.0.1",
    description="C4 Accounts Custom App",
    author="Connect4systems",
    author_email="",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
