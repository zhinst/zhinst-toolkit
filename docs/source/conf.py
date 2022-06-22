# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))


# -- Project information -----------------------------------------------------

project = "zhinst-toolkit"
copyright = "2020, Zurich Instruments AG"
author = "Zurich Instruments AG"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.viewcode",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx_issues",
    "nbsphinx",
    "nbsphinx_link",
    "IPython.sphinxext.ipython_console_highlighting",
    "m2r2",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
]
add_module_names = False
# Autodoc settings
autodoc_default_options = {"show-inheritance": True}
autodoc_typehints = "both"
autodoc_typehints_format = "short"
autosummary_generate = True
set_type_checking_flag = False

# Sphinx issues
issues_github_path = "zhinst/zhinst-toolkit"

# Make sure the target is unique
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

nbsphinx_execute = "never"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "**.ipynb_checkpoints"]

from importlib.metadata import version

version = version("zhinst.toolkit")


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_css_files = ['zhinst-sphinx-theme/css/custom.css']

html_theme_options = {
    "logo": {
        "text": "zhinst-toolkit",
    }
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# nbsphinx parameters

nbsphinx_codecell_lexer = "none"
highlight_language = "none"

# Spelling
# sphinxcontrib.spelling configuration file
spelling_word_list_filename='spelling_wordlist.txt'
# Show suggestion in console output
spelling_show_suggestions=False
spelling_exclude_patterns=['examples/*.nblink', 'source/_static/zhinst-sphinx-theme/**/*']
