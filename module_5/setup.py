from setuptools import setup, find_packages

setup(
    name="module_5_gradcafe_analytics",
    version="0.1.0",
    # find_packages() automatically finds the 'src' or other internal modules
    packages=find_packages(),
    # These are the core runtime dependencies from your requirements.txt
    install_requires=[
        "flask>=3.0.0",
        "psycopg[binary]>=3.2.0",
        "python-dotenv>=1.0.1",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.3",
        "huggingface_hub",
        "llama-cpp-python",
        "reportlab>=4.0.0",
        "pillow==12.1.1",
    ],
    # You can also add development tools as optional extras
    extras_require={
        "dev": [
            "pylint>=3.0.0",
            "pydeps>=1.12.20",
            "pytest>=7.4.0",
            "sphinx>=7.0.0",
        ],
    },
    author="Eugene Buyanovsky",
    description="A reproducible GradCafe analytics application with hardened database access.",
)
