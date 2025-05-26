"""
Setup script for mail-agent package
"""
from setuptools import setup, find_packages

setup(
    name="mail-agent",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "authlib>=1.5.2",
        "flask>=3.1.1",
        "flask-sqlalchemy>=3.1.1",
        "flask-wtf>=1.2.2",
        "google-api-python-client>=2.169.0",
        "google-auth>=2.40.2",
        "google-auth-httplib2>=0.2.0",
        "google-auth-oauthlib>=1.2.2",
        "click>=8.1.3",
        ],
    entry_points={
        "console_scripts": [
            "mactl=mail_agent.cli:cli",
        ],
    },
)
