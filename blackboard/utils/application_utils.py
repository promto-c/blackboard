# Type Checking Imports
# ---------------------
from typing import Tuple, Optional, List, Union

# Standard Library Imports
# ------------------------
import subprocess
import re
import os
import configparser
from enum import Enum


# Class Definitions
# -----------------
class ApplicationSection(Enum):
    DEFAULT = 'default'
    REGISTERED = 'registered'
    RECOMMENDED = 'recommended'

    def __str__(self):
        return self.value

class ApplicationUtils:
    """Utility class for handling application-related operations.

    This class provides static methods to interact with MIME types, find associated
    applications, and manage .desktop files for applications.
    """
    # Class constants for common paths
    APPLICATIONS_PATH = '/usr/share/applications/'
    USER_APPLICATIONS_PATH = os.path.expanduser('~/.local/share/applications/')

    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """Gets the MIME type of the specified file.

        Args:
            file_path (str): The path to the file for which to get the MIME type.

        Returns:
            str: The MIME type of the file.
        """
        if os.name == 'nt':
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
        else:
            mime_type = subprocess.check_output(['file', '--mime-type', '-b', file_path]).decode().strip()
        return mime_type

    @staticmethod
    def get_mime_type_associations(mime_type: str) -> dict:
        """Retrieve MIME type associations using the 'gio mime' command.

        Args:
            mime_type (str): The MIME type to search for associated applications.

        Returns:
            dict: A dictionary with keys 'default', 'registered', 'recommended' and their associated applications.
        """
        result = subprocess.check_output(['gio', 'mime', mime_type]).decode().strip()

        data = {'default': None, 'registered': [], 'recommended': []}

        patterns = {
            'default': re.compile(r'Default application for “.+?”: (.+)'),
            'registered': re.compile(r'Registered applications:\n((?:\s+.+\.desktop\n)+)'),
            'recommended': re.compile(r'Recommended applications:\n((?:\s+.+\.desktop\n)+)')
        }

        for key, pattern in patterns.items():
            match = pattern.search(result)
            if match:
                if key == 'default':
                    data[key] = match.group(1).strip()
                else:
                    data[key] = [app.strip() for app in match.group(1).strip().split('\n')]

        return data

    @staticmethod
    def get_associated_apps(mime_type: str, section: Union[ApplicationSection, str] = ApplicationSection.DEFAULT) -> Union[str, List[str]]:
        """List applications associated with a given MIME type.

        Args:
            mime_type (str): The MIME type to search for associated applications.
            section (Union[ApplicationSection, str]): The section of applications to return ('default', 'registered', 'recommended').

        Returns:
            Union[str, List[str]]: The path to the default application or a list of paths to the registered or recommended applications.

        Raises:
            ValueError: If the provided section is invalid.
        """
        # Convert section to ApplicationSection if it's a string
        if isinstance(section, str):
            try:
                section = ApplicationSection(section.lower())
            except ValueError:
                raise ValueError(f"Invalid section '{section}'. Choose from 'default', 'registered', 'recommended'.")

        # Fetch the associated applications data for the given MIME type
        parsed_data = ApplicationUtils.get_mime_type_associations(mime_type)

        # Validate and return the requested section
        if section not in ApplicationSection:
            raise ValueError(f"Invalid section '{section.value}'. Choose from 'default', 'registered', 'recommended'.")

        # Return the appropriate data based on the section
        if section == ApplicationSection.DEFAULT:
            return ApplicationUtils.find_desktop_file(parsed_data[section.value])
        else:
            return ApplicationUtils.find_desktop_files(parsed_data[section.value])

    @staticmethod
    def parse_desktop_file(desktop_file: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse the .desktop file to extract the application name and icon path.

        Args:
            desktop_file (str): Path to the .desktop file.

        Returns:
            Tuple[Optional[str], Optional[str]]: The application name and icon path, or None if not found.
        """
        config = configparser.ConfigParser()
        config.read(desktop_file)

        name = config.get('Desktop Entry', 'Name', fallback=None)
        icon = config.get('Desktop Entry', 'Icon', fallback=None)

        return name, icon

    @staticmethod
    def find_desktop_file(app_name: str) -> Optional[str]:
        """Find the full path of the .desktop file for the specified application.

        Args:
            app_name (str): The name of the application for which to find the .desktop file.

        Returns:
            Optional[str]: The full path to the .desktop file, or None if not found.
        """
        search_paths = [ApplicationUtils.APPLICATIONS_PATH, ApplicationUtils.USER_APPLICATIONS_PATH]
        for path in search_paths:
            desktop_file = os.path.join(path, app_name)
            if os.path.isfile(desktop_file):
                return desktop_file
        return

    @staticmethod
    def find_desktop_files(app_list: List[str]) -> List[Optional[str]]:
        """Find the full paths of .desktop files for a list of specified applications.

        Args:
            app_list (List[str]): A list of application names for which to find .desktop files.

        Returns:
            List[Optional[str]]: A list of full paths to the .desktop files. The list will be empty if no .desktop files are found.
        """
        return [ApplicationUtils.find_desktop_file(app) for app in app_list if ApplicationUtils.find_desktop_file(app)]

    @staticmethod
    def open_file_with_application(file_path: str, desktop_file: str):
        """Command to open the file with the specified application.

        Args:
            file_path (str): The path to the file to be opened.
            desktop_file (str): The path to the .desktop file of the application to use.

        Raises:
            ValueError: If no .desktop file is found for the selected application.
        """
        if desktop_file:
            subprocess.run(['gio', 'launch', desktop_file, file_path])
        else:
            print("No .desktop file found for the selected application.")

    @staticmethod
    def open_directory_in_terminal(path: str) -> None:
        """Opens the specified directory in a new terminal window.

        Args:
            path (str): The path to open in the terminal.
        """
        if not os.path.isdir(path):
            path = os.path.dirname(path)

        if os.name == 'nt':  # Windows
            os.startfile(path)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.Popen(['xdg-open', path])
        else:
            raise NotImplementedError(f"Unsupported operating system: {os.name}")
