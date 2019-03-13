from setuptools import setup

setup(
        name = "pttt",
        version = "0.1",
        packages = [
            "pttt",
        ],
        extras_require = {
            "cli": ["click"]
        },
        scripts = [
            "scripts/pttt"
        ]
)
