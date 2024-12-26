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
import zipfile
import tempfile

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


def repackage(pkg: str, version: str, output_dir: Path, wheel_dir: Path, cross_build_files: list[str]):
    native_wheel = next(output_dir.glob(f"{pkg.replace('-', '_')}*{version}*.whl"))
    cross_compiled_wheel = next(wheel_dir.glob(f"{pkg.replace('-', '_')}*{version}*.whl"))

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        native_unpack_dir = temp_dir / "native"
        cross_unpack_dir = temp_dir / "cross"

        native_unpack_dir.mkdir()
        cross_unpack_dir.mkdir()

        # Unpack the native wheel
        with zipfile.ZipFile(native_wheel, 'r') as zip_ref:
            zip_ref.extractall(native_unpack_dir)

        # Unpack the cross-compiled wheel
        with zipfile.ZipFile(cross_compiled_wheel, 'r') as zip_ref:
            zip_ref.extractall(cross_unpack_dir)

        # Replace the cross build files in the native wheel
        for cross_build_file in cross_build_files:
            print(f"Replacing {cross_build_file}...")
            cross_file_path = cross_unpack_dir / cross_build_file
            if not cross_file_path.exists():
                print(f"Warning: {cross_build_file} not found in the cross-compiled wheel.")
                continue

            target_path = native_unpack_dir / cross_build_file
            if not target_path.exists():
                print(f"Warning: {cross_build_file} not found in the native wheel.")
                continue
            
            cross_file_path.replace(target_path)

        # Repack the native wheel
        repackaged_wheel = output_dir / native_wheel.name
        with zipfile.ZipFile(repackaged_wheel, 'w') as zip_ref:
            for file in native_unpack_dir.rglob('*'):
                zip_ref.write(file, file.relative_to(native_unpack_dir))

    print(f"Repackaged {pkg} {version} to {repackaged_wheel}")


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

        print("Repackaging the package...")
        repackage(pkgname, version, output_dir, wheel_dir, cross_build_files)


if __name__ == "__main__":
    main()