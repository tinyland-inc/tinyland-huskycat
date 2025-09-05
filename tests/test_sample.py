#!/usr/bin/env python3
"""Sample Python file for MCP validation testing."""

from typing import List


def calculate_sum(numbers: List[int]) -> int:
    """Calculate the sum of a list of numbers.

    Args:
        numbers: List of integers to sum

    Returns:
        The sum of all numbers
    """
    total = 0
    for num in numbers:
        total = total + num
    return total


def main():
    # Test the function
    test_numbers = [1, 2, 3, 4, 5]
    result = calculate_sum(test_numbers)
    print(f"Sum of {test_numbers} = {result}")

    # Potential style issue: unused variable

    # Another test
    if result > 10:
        print("Result is greater than 10")
    else:
        print("Result is 10 or less")


if __name__ == "__main__":
    main()
