import argparse
import shutil
from pathlib import Path
import time
import subprocess as sp
import os

import requests
from packaging.utils import parse_wheel_filename

SIMPLE_INDEX_URL = "https://pypi.org/simple/"
CONTENT_TYPE = "application/vnd.pypi.simple.v1+json"

SUPPORTED_ABIS = {
    "none",
    "cp312",
    "cp313",
    "cp314",
}

session = requests.Session()
session.headers.update(
    {
        "Accept": CONTENT_TYPE,
    }
)


def check_anaconda_client():
    """
    Check if the anaconda client is installed
    """

    client = shutil.which("anaconda")
    if client is None:
        print(
            "Anaconda client is not installed. Please install it using `conda install anaconda-client` or `mamba install anaconda-client`."
        )
        print(
            "The anaconda-client in PyPI is outdated, so it is recommended to use conda or mamba."
        )

        raise SystemExit(1)


def get_package_urls_PyPI(pkg: str, version: str) -> list[str]:
    """
    Get the package urls from PyPI
    """
    pkg_url = f"{SIMPLE_INDEX_URL}{pkg}/"

    r = session.get(pkg_url)
    if not r.ok:
        raise RuntimeError(
            f"Failed to get package information for {pkg} from PyPI: {r.status_code}"
        )

    data = r.json()

    versions = data["versions"]
    if version not in versions:
        raise RuntimeError(f"Version {version} is not available for package {pkg}")

    releases = reversed(data["files"])
    urls = []
    for release in releases:
        filename = release["filename"]
        url = release["url"]

        # we are only interested in wheels
        if not filename.endswith(".whl"):
            continue

        # parsed_version = str(parse_wheel_filename(filename)[1])
        # if parsed_version != version:
        #     continue
        _, parsed_version, _, parsed_tags = parse_wheel_filename(filename)
        
        if str(parsed_version) != version:
            continue

        tags = list(parsed_tags)
        if not tags:
            continue

        tag = tags[0]
        if tag.platform in ["win32", "win_amd64"]:
            # not interested in windows wheels
            continue

        if tag.platform.endswith(("i686", "i386", "armv6l", "armv7l", "s390x", "ppc64le")):
            # Exclude minority architectures for now to reduce the number of wheels
            continue

        if tag.abi not in SUPPORTED_ABIS:
            # not interested in unsupported ABIs
            continue

        urls.append(url)

    return urls


def download_wheels(urls: list[str], dest: Path, delay: int = 5):
    """
    Download the wheels to the destination directory
    """
    dest.mkdir(parents=True, exist_ok=True)

    for url in urls:
        r = session.get(url)
        if not r.ok:
            print(f"[-] Failed to download {url}")
            continue

        filename = url.split("/")[-1]
        with open(dest / filename, "wb") as f:
            f.write(r.content)

        print(f"[+] Downloaded {filename}")

        # Avoid DoS'ing the server
        time.sleep(delay)


def upload_wheels(dest: Path, token: str):
    """
    Upload the wheels to Anaconda
    """
    sp.run(
        " ".join([
            "anaconda",
            "-t",
            token,
            "upload",
            f"{dest}/*.whl",
            # skip summary to avoid size limit
            '--summary=" "',
            '--description=" "',
        ]),
        check=True,
        shell=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mirror a package from PyPI to Anaconda"
    )
    parser.add_argument("package", help="The package name")
    parser.add_argument("version", help="The package version")

    return parser.parse_args()


def main():
    args = parse_args()

    urls = get_package_urls_PyPI(args.package, args.version)
    if not urls:
        print(f"[*] No wheels found for {args.package}=={args.version}")
        return

    print(f"[*] Found {len(urls)} wheels for {args.package}=={args.version}")

    dest = Path.cwd() / f"{args.package}-{args.version}"
    download_wheels(urls, dest)

    print(f"[*] Downloaded wheels to {dest}")

    check_anaconda_client()

    token = os.environ.get("ANACONDA_API_TOKEN")
    if not token:
        raise RuntimeError("No ANACONDA_API_TOKEN found in the environment")

    print("[*] Anaconda client is installed.")

    upload_wheels(dest, token)

    print("[*] Uploaded wheels to Anaconda")


if __name__ == "__main__":
    main()