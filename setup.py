from setuptools import setup, find_packages

setup(
    name="pysoar",
    version="0.4.0",
    description="A lightweight Python SOAR framework for edge and SOHO networks",
    packages=find_packages(),
    py_modules=[
        "classes",
        "menu",
        "pysoar",
        "secrets_manager",
        "triggers",
        "playbook_validator",
        "scheduler",
        "api_server",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pymisp>=2.5.34,<2.6",
        "PyYAML>=6.0.1",
        "requests>=2.31.0",
        "pyflowchart>=0.3.1",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pysoar=pysoar:main_cli",
        ],
    },
)
