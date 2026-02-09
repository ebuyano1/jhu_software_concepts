# Configuration file for the Sphinx documentation builder.
import os
import sys

# -- Path setup --------------------------------------------------------------
# Points to the source code directory relative to module_4/docs/source/
sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------
project = 'GradCafe Analytics'
copyright = '2026, Eugene Buyanovsky'
author = 'Eugene Buyanovsky'
release = '1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',      # Core library for html generation
    'sphinx.ext.napoleon',     # Support for Google style docstrings
    'sphinx.ext.viewcode',     # Add links to highlighted source code
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'
html_static_path = ['_static']