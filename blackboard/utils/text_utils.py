# Type Checking Imports
# ---------------------
from typing import List, Tuple, Dict

# Standard Library Imports
# ------------------------
import re
from difflib import SequenceMatcher


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
    def extract_terms(input_text: str) -> Tuple[List[str], List[str]]:
        """Extracts quoted and unquoted terms from the given input text, supporting multiple delimiters.

        Quoted terms are extracted from both double quotes (") and single quotes (').
        Unquoted terms are split based on the specified delimiters.

        Args:
            input_text (str): The input text containing quoted and unquoted terms.

        Returns:
            Tuple[List[str], List[str]]: A tuple containing:
                quoted_terms (List[str]): List of terms extracted from quotes.
                unquoted_terms (List[str]): List of terms extracted outside quotes and split by delimiters.

        Examples:
            >>> TextExtraction.extract_terms('''
            ... "apple", 'banana', orange, som'e'word | 'mango, tree', cat' house\\n another word
            ... ''')
            (['apple', 'banana', 'mango, tree'], ['orange', "som'e'word", "cat' house", 'another word'])

            >>> TextExtraction.extract_terms('"apple" | "banana" | "orange"')
            (['apple', 'banana', 'orange'], [])

            >>> TextExtraction.extract_terms("'apple' 'banana' 'orange'")
            (['apple', 'banana', 'orange'], [])

            >>> TextExtraction.extract_terms("'apple', 'banana', orange, 'mango, tree'")
            (['apple', 'banana', 'mango, tree'], ['orange'])
        """
        if not input_text:
            return [], []

        pattern = re.compile(r'''
            \s*             # Match any leading spaces (ignored in results)
            "([^"]*)"       # Capture anything within double quotes in group 1
            \s*             # Match any trailing spaces (ignored in results)
        |                   # OR
            \s*             # Match any leading spaces (ignored in results)
            '([^']*)'       # Capture anything within single quotes in group 2
            \s*             # Match any trailing spaces (ignored in results)
        |                   # OR
            \s*             # Match any leading spaces (ignored in results)
            ([^\t\n,|]+)    # Capture any sequence of characters that aren't delimiters or quotes in group 3
            \s*             # Match any trailing spaces (ignored in results)
        ''', re.VERBOSE)

        # Find all matches based on the pattern, this ignores empty matches by the nature of the regex
        matches: List[Tuple[str, str, str]] = pattern.findall(input_text)

        # Initialize lists for different captured groups
        double_quoted_terms, single_quoted_terms, unquoted_terms = [
            [stripped_term for term in group if (stripped_term := term.strip())] 
            for group in zip(*matches)
        ]

        return double_quoted_terms + single_quoted_terms, unquoted_terms

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
    
class TextMapping:

    def map_similar_texts(inputs: List[str], match_candidates: List[str]) -> Dict[str, str]:
        """Map each item in `inputs` to the most similar item in `match_candidates` by maximizing overall match quality.

        Args:
            inputs (List[str]): List of input strings to map.
            match_candidates (List[str]): List of candidate strings to match against.

        Returns:
            Dict[str, str]: Dictionary mapping each input string to its best match in `match_candidates`.

        Examples:
            >>> inputs = ["alpha_v1", "beta_v2", "gamma_v1"]
            >>> match_candidates = ["alpha_final", "beta_final", "gamma_release"]
            >>> TextMapping.map_similar_texts(inputs, match_candidates)
            {'alpha_v1': 'alpha_final', 'beta_v2': 'beta_final', 'gamma_v1': 'gamma_release'}

            >>> inputs = ["task_A", "task_C", "task_B"]
            >>> match_candidates = ["task_3", "task_1", "task_2", "task_4"]
            >>> TextMapping.map_similar_texts(inputs, match_candidates)
            {'task_A': 'task_1', 'task_B': 'task_2', 'task_C': 'task_3'}
        """
        # Create a scoring matrix with (input, candidate, score) tuples
        scores: List[Tuple[str, str, float]] = [
            (input_text, candidate, SequenceMatcher(None, input_text, candidate).ratio())
            for input_text in inputs
            for candidate in match_candidates
        ]

        # Sort by score (descending), input text (alphabetically), and candidate name (alphabetically)
        scores.sort(key=lambda x: (-x[2], x[0], x[1]))

        # Initialize mapping and track used candidates
        mapping: Dict[str, str] = {}
        used_candidates = set()

        # Go through the sorted pairs, prioritizing higher scores
        for input_text, candidate, score in scores:
            if input_text in mapping or candidate in used_candidates:
                continue
            mapping[input_text] = candidate
            used_candidates.add(candidate)

        return mapping


if __name__ == "__main__":
    import doctest
    doctest.testmod()
