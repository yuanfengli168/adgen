from setuptools import setup, find_packages

setup(
    name="adgen",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["requests>=2.31", "click>=8.1", "Pillow>=10.0"],
    entry_points={"console_scripts": ["adgen=adgen.cli:cli"]},
)