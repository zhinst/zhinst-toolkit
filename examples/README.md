# Zurich Instruments Toolkit (zhinst-toolkit) Examples

This directory contains the examples for zhinst-toolkit.

We use [jupytext](https://github.com/mwouts/jupytext) to version control our
examples. Meaning that all our examples are uploaded in markdown, although they
are written in jupyter notebooks. To convert a example back into a notebook
simply do:

```
jupytext --to ipynb examples/hf2.md
```

We`ve also a script called [generate_notebooks.sh](generate_notebooks.sh) that
automatically syncs/creates the notebooks.
