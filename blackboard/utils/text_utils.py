# Type Checking Imports
# ---------------------
from typing import List

# Standard Library Imports
# ------------------------
import re


# Class Definitions
# -----------------
class TextUtil:
    """Provides static methods for various text-related operations.
    """

    @staticmethod
    def find_positions(text: str, substring: str, case_sensitive: bool = True) -> List[int]:
        """Find all positions of a substring within a text.

        Args:
            text (str): The text in which to search for positions of the substring.
            substring (str): The substring to search for within the text.
            case_sensitive (bool, optional): If False, perform a case-insensitive search (default is True).

        Returns:
            List[int]: A list of indices where the substring is found in the text.

        Example:
        >>> text = "This is a test sentence. This test has multiple occurrences. Test is repeated to test the function."
        >>> TextUtil.find_positions(text, "test")
        [10, 30, 81]
        >>> TextUtil.find_positions(text, "test", case_sensitive=False)
        [10, 30, 61, 81]
        """
        indexes = []
        sub_len = len(substring)

        if not case_sensitive:
            text = text.lower()
            substring = substring.lower()

        start_find = 0
        while True:
            index = text.find(substring, start_find)
            if index == -1:
                break
            indexes.append(index)
            start_find = index + sub_len

        return indexes

class TextExtraction:
    """Provides static methods for extracting quoted and unquoted terms from strings.
    """

    @staticmethod
    def extract_quoted_terms(keyword: str) -> List[str]:
        """Extracts terms enclosed in quotes from the given keyword string.

        Terms enclosed in either double or single quotes are considered quoted terms.

        Args:
            keyword: The keyword string containing the terms.

        Returns:
            A list of quoted terms.

        Example:
            >>> TextExtraction.extract_quoted_terms("'apple' \\" banana\\" grape \\"orange and mango\\"")
            ['apple', 'banana', 'orange and mango']
        """
        quoted_terms = re.findall(r'"(.*?)"|\'(.*?)\'', keyword)
        return [term.strip() for terms in quoted_terms for term in terms if term.strip()]

    @staticmethod
    def extract_unquoted_terms(keyword: str) -> List[str]:
        """Extracts terms not enclosed in quotes from the given keyword string.

        Terms not enclosed in quotes are considered unquoted terms, split on tabs,
        new lines, commas, or pipes.

        Args:
            keyword: The keyword string containing the terms.

        Returns:
            A list of unquoted terms.

        Example:
            >>> TextExtraction.extract_unquoted_terms("'apple' \\" banana\\" grape \\"orange and mango\\"")
            ['grape']
        """
        unquoted_terms = [term.strip() for term in re.split(r'"[^"]*"|\'[^\']*\'', keyword) if term.strip()]
        return [split_term for term in unquoted_terms for split_term in TextExtraction.split_keywords(term) if split_term.strip()]

    @staticmethod
    def split_keywords(text: str) -> List[str]:
        """Splits the given text into keywords based on common delimiters.

        Args:
            text: A string to be split.

        Returns:
            A list of split keywords.

        Examples:
            >>> TextExtraction.split_keywords('apple, banana|grape\\torange\\nmango')
            ['apple', ' banana', 'grape', 'orange', 'mango']
        """
        return re.split('[\t\n,|]+', text)

    @staticmethod
    def is_contains_wildcard(text: str) -> bool:
        """Checks if the given text contains any wildcard characters ('*' or '?').

        Args:
            text: A string in which to check for wildcards.

        Returns:
            True if wildcards are present, False otherwise.

        Examples:
            >>> TextExtraction.is_contains_wildcard('apple*')
            True
            >>> TextExtraction.is_contains_wildcard('banana')
            False
        """
        return '*' in text or '?' in text

if __name__ == "__main__":
    import doctest
    doctest.testmod()
