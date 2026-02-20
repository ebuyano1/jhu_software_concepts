from setuptools import setup, find_packages

setup(
    name="module_5_gradcafe_analytics",
    version="0.1.0",
    packages=find_packages(where="src"), # Correctly finds modules in /src
    package_dir={"": "src"},             # Maps the root to /src
    install_requires=[
        "flask>=3.0.0",
        "psycopg[binary]>=3.2.0",
        "python-dotenv>=1.0.1",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.3",
        "huggingface_hub",
        "llama-cpp-python",
        "reportlab>=4.0.0",
        "pillow==12.1.1", # Critical security fix for vulnerabilities
    ],
    extras_require={
        "dev": [
            "pylint>=3.0.0",
            "pydeps>=1.12.20",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",   # Added for CI Coverage enforcement
            "pytest-mock>=3.12.0",  # Added to match requirements.txt
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=2.0.0", # Added to match requirements.txt
        ],
    },
    author="Eugene Buyanovsky",
    description="A reproducible GradCafe analytics application with hardened database access.",
)