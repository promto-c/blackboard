"""
Copyright (C) 2024 promto-c

Permission Notice:
- You are free to use, copy, modify, and distribute this software for any purpose.
- No restrictions are imposed on the use of this software.
- You do not need to give credit or include this notice in your work.
- Use at your own risk.
- This software is provided "AS IS" without any warranty, either expressed or implied.

Note: This code is intended primarily as an example. While you can use it freely as described above, be aware that it utilizes qtpy, which is licensed under GPL v3. Ensure you adhere to qtpy's licensing terms when using or distributing this code.
"""
# Type Checking Imports
# ---------------------
from typing import List

# Standard Library Imports
# ------------------------
import fnmatch
from pathlib import Path


# Function Definitions
# --------------------
def read_ignore_patterns(root_path: Path) -> List[str]:
    """Reads .gitignore file and returns a list of ignore patterns.
    
    Args:
        root_path (Path): The root directory path of the repository.
    
    Returns:
        List[str]: A list of patterns to ignore.
    """
    ignore_patterns = ['.git/']  # Include .git directory by default
    gitignore_path = root_path / '.gitignore'
    if gitignore_path.exists():
        with gitignore_path.open('r') as file:
            ignore_patterns.extend(file.read().splitlines())
    return ignore_patterns

def is_ignored(path: Path, ignore_patterns: List[str]) -> bool:
    """Determines if a given path should be ignored based on the ignore patterns.
    
    Args:
        path (Path): The path to check.
        ignore_patterns (List[str]): Patterns defining which paths to ignore.
    
    Returns:
        bool: True if the path should be ignored, False otherwise.
    """
    relative_path = path.relative_to(Path.cwd())
    return any(fnmatch.fnmatch(relative_path.as_posix(), pattern.strip('/')) or 
               fnmatch.fnmatch(relative_path.name, pattern.strip('/')) for pattern in ignore_patterns)

def print_structure(root_path: Path, ignore_patterns: List[str], only_dirs: bool = False, prefix: str = ''):
    """Prints the repository structure, optionally filtering to only show directories.
    
    Args:
        root_path (Path): The root directory path to print.
        ignore_patterns (List[str]): Patterns defining which paths to ignore.
        only_dirs (bool): If True, only directories are printed.
        prefix (str): Prefix for the printed directory structure.
    """
    entries = sorted(root_path.iterdir(), key=lambda x: (x.is_file(), x.name))
    for index, entry in enumerate(entries):
        if is_ignored(entry, ignore_patterns):
            continue

        if entry.is_dir() or not only_dirs:
            connector = '├──' if index < len(entries) - 1 else '└──'
            print(f"{prefix}{connector} {entry.name}")
            if entry.is_dir():
                new_prefix = '│   ' if index < len(entries) - 1 else '    '
                print_structure(entry, ignore_patterns, only_dirs, prefix + new_prefix)

# Main Function
# -------------
def main(repo_path: str | Path, only_dirs: bool = False):
    """Main function to print the structure of a repository.
    
    Args:
        repo_path (Union[str, Path]): The path to the repository.
        only_dirs (bool): If True, only directories are printed.
    """
    root_path = Path(repo_path).resolve()
    ignore_patterns = read_ignore_patterns(root_path)
    print(f"{root_path.name}/")
    print_structure(root_path, ignore_patterns, only_dirs)

if __name__ == '__main__':
    repo_path = ''  # Specify the path to your repository here
    only_dirs = False  # Change to True if you want to list only directories
    main(repo_path, only_dirs)
