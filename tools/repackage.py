"""
Repackages a package so it can be used as a build dependency when cross-compiling packages into Pyodide.

What this script does:

- Downloads the "native" wheel file from PyPI.
- Replace a few files in the wheel file with ones from the cross-compiled packages.
  - These files are called, "cross build files", and often they are header files or static libraries that are needed to build other packages.
"""

import argparse
import subprocess as sp
import sys
from pathlib import Path

# private API, don't use outside of this script
from pyodide_build.recipe import load_all_recipes

def parse_args():
    parser = argparse.ArgumentParser(description="Repackages a package so it can be used as a build dependency when cross-compiling packages into Pyodide.")
    parser.add_argument("-r", "--recipe-dir", help="The directory containing the recipe for the package.", default="packages")
    parser.add_argument("-w", "--wheel-dir", help="The directory containing the wheel file for the package.", default="dist")
    parser.add_argument("-o", "--output-dir", help="The directory to output the repackaged wheel file.", default="out")

    return parser.parse_args()


def download_native_package(pkg: str, version: str, output_dir: str):
    sp.run([
        sys.executable,
        "-m",
        "pip",
        "download",
        f"{pkg}=={version}",
        "--no-deps",
        "-d",
        output_dir,
    ])


def main():
    args = parse_args()
    recipe_dir = Path(args.recipe_dir).resolve()
    wheel_dir = Path(args.wheel_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    recipes = load_all_recipes(recipe_dir)

    for recipe in recipes.values():
        pkgname = recipe.package.name
        version = recipe.package.version
        package_type = recipe.build.package_type
        cross_build_files = recipe.build.cross_build_files

        if package_type != "package" or not cross_build_files:
            print(f"Skipping {pkgname} {version} because it doesn't have any cross build files.")
            continue

        print(f"Repackaging {pkgname} {version}...")

        print("Downloading the native package...")
        download_native_package(pkgname, version, str(output_dir))

    print(args)


if __name__ == "__main__":
    main()