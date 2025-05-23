from setuptools import setup, find_packages

setup(
    name="meeting-rescheduler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gradio>=4.19.2",
        "openai>=1.13.3",
        "google-auth-oauthlib>=1.2.0",
        "google-auth>=2.28.1",
        "google-api-python-client>=2.120.0",
        "python-dotenv>=1.0.1",
        "pytest>=8.0.2",
        "pytest-asyncio>=0.23.5",
    ],
    python_requires=">=3.11",
) 