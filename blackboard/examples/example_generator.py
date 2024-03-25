import os

def generate_file_paths(start_path):
    """Generates file paths in the given directory and its subdirectories.

    Args:
        start_path: A string representing the starting directory path.

    Yields:
        Full path of each file found in the directory and subdirectories.
    """
    for root, dirs, files in os.walk(start_path):
        for file in files:
            yield {'file_path': os.path.join(root, file)}
