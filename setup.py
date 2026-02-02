from setuptools import setup, find_packages

setup(
    name="kitchen_rl",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy",
        "networkx",
        "gymnasium",
        "stable-baselines3",
        "sb3-contrib",
        "pyyaml"
    ],
)