#!/usr/bin/env python3
# ruff: noqa: T201
"""
Script to update the Swagger UI files to the latest version.

This script:
1. Checks the current version of Swagger UI
2. Gets the latest version of Swagger UI from GitHub
3. Downloads and extracts the latest version if needed
4. Updates the UI files in the project
5. Updates version information in the README and VERSION file
"""

import json
import logging
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

import requests

from aiohttp_apigami.swagger_ui import SWAGGER_UI_STATIC_FILES, SWAGGER_UI_VERSION_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("update_swagger_ui")

# Constants
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CURRENT_DIR.parent
README_PATH = PROJECT_DIR / "README.md"
SWAGGER_UI_REPO = "swagger-api/swagger-ui"
GITHUB_API_TIMEOUT = 120  # seconds
REQUEST_TIMEOUT = 300  # seconds

# Custom JavaScript to inject into the index.html file
INDEX_JAVASCRIPT = """
    window.onload = function() {
      // Begin Swagger UI call region
      window.ui = SwaggerUIBundle({
        url: "$path",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "$layout",
      });
      // End Swagger UI call region
    };
  """


def get_current_version() -> str:
    """
    Get the current Swagger UI version from the VERSION file.

    Returns:
        str: The current Swagger UI version
    """
    try:
        with SWAGGER_UI_VERSION_PATH.open("r", encoding="utf-8") as file:
            return file.read().strip()
    except (OSError, FileNotFoundError) as e:
        logger.warning("Could not read current version: %s", e)
        return "unknown"


def detect_latest_release(repo: str) -> str:
    """
    Get the latest version of a GitHub repository using the GitHub API.

    Args:
        repo (str): GitHub repository in the format 'owner/repo'

    Returns:
        str: The latest version tag

    Raises:
        ValueError: If unable to get the latest version
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    logger.info("Checking latest release from %s", url)

    try:
        resp = requests.get(url, timeout=GITHUB_API_TIMEOUT)
        resp.raise_for_status()
        latest = resp.json()
        tag: str | None = latest.get("tag_name")

        if not tag:
            raise ValueError("No tag found in GitHub API response")

        logger.info("%s latest version is %s", repo, tag)
        return tag
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to fetch latest release: %s", e)
        raise ValueError(f"Could not determine latest version: {e}") from e


def get_latest_version() -> str:
    """
    Get the latest version of Swagger UI.

    Returns:
        str: The latest Swagger UI version
    """
    return detect_latest_release(SWAGGER_UI_REPO)


def download_file(url: str, target_path: Path) -> None:
    """
    Download a file from a URL to the specified path.

    Args:
        url (str): The URL to download from
        target_path (Path): The path to save the file to

    Raises:
        ValueError: If download fails
    """
    try:
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as resp:
            resp.raise_for_status()
            with target_path.open("wb") as f:
                shutil.copyfileobj(resp.raw, f)
        logger.info("Downloaded %s to %s", url, target_path)
    except (OSError, requests.RequestException) as e:
        logger.error("Failed to download %s: %s", url, e)
        raise ValueError(f"Download failed: {e}") from e


def unpack_archive(tar_path: Path, target_dir: Path) -> Path:
    """
    Unpack a tar file to a directory.

    Args:
        tar_path (Path): Path to the tar file
        target_dir (Path): Directory to extract to

    Returns:
        Path: Path to the extracted directory

    Raises:
        ValueError: If extraction fails
    """
    try:
        with tarfile.open(tar_path) as tar_file:
            tar_file.extractall(path=target_dir)
            extract_dirname = tar_file.getnames()[0]
        return target_dir / extract_dirname
    except (OSError, tarfile.TarError) as e:
        logger.error("Failed to extract %s: %s", tar_path, e)
        raise ValueError(f"Extraction failed: {e}") from e


def copy_dist_files(dist_dir: Path, dest_dir: Path) -> None:
    """
    Copy distribution files to the destination directory.

    Args:
        dist_dir (Path): Source directory with distribution files
        dest_dir (Path): Destination directory

    Raises:
        ValueError: If copy fails
    """
    try:
        for path in dist_dir.glob("**/*"):
            if path.is_file():
                dst_path = dest_dir / path.relative_to(dist_dir)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dst_path)
                logger.debug("Copied %s to %s", path, dst_path)
        logger.info("Copied files from %s to %s", dist_dir, dest_dir)
    except (OSError, shutil.Error) as e:
        logger.error("Failed to copy distribution files: %s", e)
        raise ValueError(f"File copy failed: {e}") from e


def update_index_html(index_path: Path) -> None:
    """
    Update the index.html file with custom JavaScript and proper paths.

    Args:
        index_path (Path): Path to the index.html file

    Raises:
        ValueError: If update fails
    """
    logger.info("Updating %s", index_path)

    try:
        with index_path.open("r") as html_file:
            html = html_file.read()

        # Fix asset paths
        html = re.sub(r'src="(\./dist/|\./|(?!{{))', 'src="$static/', html)
        html = re.sub(r'href="(\./dist/|\./|(?!{{))', 'href="$static/', html)

        # Replace the Swagger initializer script
        html = re.sub(
            r'<script .*/swagger-initializer.js".*</script>',
            f"<script>{INDEX_JAVASCRIPT}</script>",
            html,
        )

        # If that didn't work, try the window.onload approach
        if INDEX_JAVASCRIPT not in html:
            html = re.sub(
                r"window.onload = function\(\) {.*};$", INDEX_JAVASCRIPT, html, flags=re.MULTILINE | re.DOTALL
            )

        with index_path.open("w") as html_file:
            html_file.write(html)

        logger.info("Updated %s", index_path)
    except (OSError, re.error) as e:
        logger.error("Failed to update index.html: %s", e)
        raise ValueError(f"Index.html update failed: {e}") from e


def update_readme(version: str) -> None:
    """
    Update the README.md file with the new Swagger UI version.

    Args:
        version (str): The new Swagger UI version

    Raises:
        ValueError: If update fails
    """
    logger.info("Updating README with version %s", version)

    try:
        with README_PATH.open("r", encoding="utf-8") as file:
            readme = file.read()

        start_tag = "<!-- SWAGGER_UI_VERSION_START -->"
        end_tag = "<!-- SWAGGER_UI_VERSION_END -->"
        pattern = rf"{start_tag}(.+){end_tag}"
        new_text = f"{start_tag}[{version}](https://github.com/swagger-api/swagger-ui/releases/tag/{version}){end_tag}"

        updated_readme, count = re.subn(pattern, new_text, readme)

        if count > 0:
            with README_PATH.open("w", encoding="utf-8") as file:
                file.write(updated_readme)
            logger.info("Updated README with Swagger UI version %s", version)
        else:
            logger.warning("No Swagger UI version reference found in README")
    except (OSError, re.error) as e:
        logger.error("Failed to update README: %s", e)
        raise ValueError(f"README update failed: {e}") from e


def update_current_version(version: str) -> None:
    """
    Update the VERSION file with the new Swagger UI version.

    Args:
        version (str): The new Swagger UI version

    Raises:
        ValueError: If update fails
    """
    try:
        SWAGGER_UI_VERSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SWAGGER_UI_VERSION_PATH.open("w", encoding="utf-8") as file:
            file.write(version)
        logger.info("Updated VERSION file to %s", version)
    except OSError as e:
        logger.error("Failed to update VERSION file: %s", e)
        raise ValueError(f"VERSION file update failed: {e}") from e


def ensure_directory_exists(path: Path) -> None:
    """
    Ensure a clean directory exists (removes it if it exists, then creates it).

    Args:
        path (Path): Directory path

    Raises:
        ValueError: If directory creation fails
    """
    try:
        if path.exists():
            shutil.rmtree(path)
            logger.info("Cleaned directory %s", path)

        path.mkdir(parents=True, exist_ok=True)
        logger.info("Ensured directory %s exists", path)
    except OSError as e:
        logger.error("Failed to prepare directory %s: %s", path, e)
        raise ValueError(f"Directory preparation failed: {e}") from e


def download_and_update_swagger_ui(version: str) -> None:
    """
    Download and update Swagger UI files to the specified version.

    Args:
        version (str): The version to download

    Raises:
        ValueError: If download or update fails
    """
    logger.info("Starting download and update of Swagger UI %s", version)

    # Use a temporary directory for downloads and extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tar_path = temp_path / f"{version}.tar.gz"

        # Download archive
        archive_url = f"https://github.com/{SWAGGER_UI_REPO}/archive/{version}.tar.gz"
        logger.info("Downloading archive from %s", archive_url)
        download_file(archive_url, tar_path)

        # Extract archive
        logger.info("Extracting %s", tar_path)
        swagger_ui_dir = unpack_archive(tar_path, temp_path)

        # Ensure clean destination directory
        ensure_directory_exists(SWAGGER_UI_STATIC_FILES)

        # Copy distribution files
        copy_dist_files(swagger_ui_dir / "dist", SWAGGER_UI_STATIC_FILES)

        # Update index.html
        update_index_html(SWAGGER_UI_STATIC_FILES / "index.html")

        # Update version references
        update_current_version(version)
        update_readme(version)

    logger.info("Successfully updated Swagger UI to version %s", version)


def main() -> int:
    """
    Main function to update Swagger UI.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        # Get current and latest versions
        current_version = get_current_version()
        logger.info("Current Swagger UI version: %s", current_version)

        latest_version = get_latest_version()
        logger.info("Latest Swagger UI version: %s", latest_version)

        # Check if update is needed
        if current_version == latest_version:
            logger.info("Swagger UI is already up to date (%s)", latest_version)
            return 0

        # Download and update if needed
        logger.info("Updating Swagger UI from %s to %s", current_version, latest_version)
        download_and_update_swagger_ui(latest_version)

        logger.info("Swagger UI update completed successfully")
        return 0

    except Exception as e:
        logger.exception("Failed to update Swagger UI: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
