# pyodide-build-deps

This repository pushes packages to the [Package index](https://anaconda.org/pyodide-build/) used by [pyodide-build](https://github.com/pyodide/pyodide-build).

## Terminologies

- The **build**: is the machine where we build programs.

- The **host**: is the machine/system where the built programs will run.

## What is this repository for?

Python is bad at cross-compiling. Let's say you want to build a Python package that uses numpy in the build process.

To build this package, numpy needs to be installed and imported during the build step.
The problem is that, you can only install and import numpy that corresponds to the **build** platform.

So, if you want to build this package against Pyodide (= WebAssembly = 32-bit architecture),
but if your host platform is 64-bit (which will be the case if you are using a modern computer),
you'll likely have issues in the build process.

Therefore, pyodide-build "fakes" the build environment by replacing a few "cross-build-files" of the package.
For instance, we replace `_numpyconfig.h` in the numpy package with a 32-bit version. This way, the package can be built against Pyodide even if the host is 64-bit.

To achieve this, this repository contains the following:

### `packages`

This directory contains the package recipes that has so called "cross-build-files" that needs to be replaced.

### `tools/repackage.py`

This python script replaces the "cross-build-files" in the native package with the "cross-build-files" that are compatible with Pyodide.

### `tools/mirror-package.py`

This python script simply mirrors the package from `PyPI` to `anaconda.org/pyodide-build`.

This script can be run in the GitHub Actions workflow to mirror the package to the alternative index.

## FAQ

### Why is `mirror-package.py` needed? Can't we just use PyPI to install them?

The problem is that if we use multiple index URLs when installing a package, there is no priority order.

For instance, let's assume that we have a package with the following build dependencies:

- numpy
- setuptools

For numpy, we cannot use PyPI as we need to replace the "cross-build-files". So we need to replace the index url.
For setuptools, we can use PyPI as it doesn't have any "cross-build-files".

However, if we set multiple index urls, there is no guarantee that the package will be installed from the correct index.
That is, numpy might be installed from PyPI, which will cause the build to fail.

Therefore, we need to mirror the whole build dependencies to the alternative index to avoid this issue.
