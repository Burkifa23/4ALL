GOLDEN_SET = [
    # --- Problem 1: Two Sum ---
    {
        "id": "two_sum_brute",
        "problem": "Two Sum",
        "code": """
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
""",
        "true_big_o": "O(N^2)",
        "efficiency_score": 1,
        "style_score": 4,
        "justification": "Brute force nested loop, correct and readable, but not optimal.",
    },
    {
        "id": "two_sum_decent",
        "problem": "Two Sum",
        "code": """
def two_sum(nums, target):
    sorted_nums = sorted(nums)
    left, right = 0, len(sorted_nums) - 1
    while left < right:
        s = sorted_nums[left] + sorted_nums[right]
        if s == target:
            return [left, right]
        elif s < target:
            left += 1
        else:
            right -= 1
""",
        "true_big_o": "O(N log N)",
        "efficiency_score": 3,
        "style_score": 3,
        "justification": "Sorting first improves on brute force but loses original indices and is slower than a hashmap.",
    },
    {
        "id": "two_sum_optimal",
        "problem": "Two Sum",
        "code": """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 5,
        "justification": "Optimal hashmap approach, clean and idiomatic.",
    },
    # --- Problem 2: Valid Parentheses ---
    {
        "id": "valid_parens_brute",
        "problem": "Valid Parentheses",
        "code": """
def is_valid(s):
    while "()" in s or "[]" in s or "{}" in s:
        s = s.replace("()", "").replace("[]", "").replace("{}", "")
    return s == ""
""",
        "true_big_o": "O(N^2)",
        "efficiency_score": 1,
        "style_score": 2,
        "justification": "Repeated string replacement in a loop is quadratic and hard to follow.",
    },
    {
        "id": "valid_parens_decent",
        "problem": "Valid Parentheses",
        "code": """
def is_valid(s):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for char in s:
        if char in "([{":
            stack.append(char)
        elif char in pairs:
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
    return len(stack) == 0
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 4,
        "justification": "Optimal stack-based approach, correct and reasonably clean.",
    },
    {
        "id": "valid_parens_optimal",
        "problem": "Valid Parentheses",
        "code": """
def is_valid(s):
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for char in s:
        if char in pairs.values():
            stack.append(char)
        else:
            if not stack or pairs.get(char) != stack.pop():
                return False
    return not stack
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 5,
        "justification": "Same optimal complexity as the decent version, but slightly tighter and more idiomatic.",
    },
    # --- Problem 3: Reverse a String ---
    {
        "id": "reverse_string_brute",
        "problem": "Reverse a String",
        "code": """
def reverse_string(s):
    result = ""
    for char in s:
        result = char + result
    return result
""",
        "true_big_o": "O(N^2)",
        "efficiency_score": 1,
        "style_score": 3,
        "justification": "String concatenation in a loop is quadratic in Python since strings are immutable.",
    },
    {
        "id": "reverse_string_decent",
        "problem": "Reverse a String",
        "code": """
def reverse_string(s):
    chars = list(s)
    left, right = 0, len(chars) - 1
    while left < right:
        chars[left], chars[right] = chars[right], chars[left]
        left += 1
        right -= 1
    return "".join(chars)
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 4,
        "justification": "Two-pointer in-place swap is optimal and clear, though more verbose than needed.",
    },
    {
        "id": "reverse_string_optimal",
        "problem": "Reverse a String",
        "code": """
def reverse_string(s):
    return s[::-1]
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 5,
        "justification": "Same optimal complexity, maximally idiomatic Python.",
    },
    # --- Problem 4: Find Max in Array ---
    {
        "id": "find_max_brute",
        "problem": "Find Max in Array",
        "code": """
def find_max(nums):
    max_val = nums[0]
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[j] > max_val:
                max_val = nums[j]
    return max_val
""",
        "true_big_o": "O(N^2)",
        "efficiency_score": 1,
        "style_score": 2,
        "justification": "Unnecessary nested loop for a problem that only needs a single pass.",
    },
    {
        "id": "find_max_decent",
        "problem": "Find Max in Array",
        "code": """
def find_max(nums):
    max_val = nums[0]
    for i in range(1, len(nums)):
        if nums[i] > max_val:
            max_val = nums[i]
    return max_val
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 4,
        "justification": "Optimal single-pass approach, clear and correct.",
    },
    {
        "id": "find_max_optimal",
        "problem": "Find Max in Array",
        "code": """
def find_max(nums):
    return max(nums)
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 5,
        "justification": "Same optimal complexity, using Python's built-in for maximum clarity.",
    },
    # --- Problem 5: Check for Duplicates ---
    {
        "id": "check_duplicates_brute",
        "problem": "Check for Duplicates",
        "code": """
def has_duplicates(nums):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j]:
                return True
    return False
""",
        "true_big_o": "O(N^2)",
        "efficiency_score": 1,
        "style_score": 4,
        "justification": "Brute force pairwise comparison, correct and readable, but not optimal.",
    },
    {
        "id": "check_duplicates_decent",
        "problem": "Check for Duplicates",
        "code": """
def has_duplicates(nums):
    sorted_nums = sorted(nums)
    for i in range(1, len(sorted_nums)):
        if sorted_nums[i] == sorted_nums[i - 1]:
            return True
    return False
""",
        "true_big_o": "O(N log N)",
        "efficiency_score": 3,
        "style_score": 3,
        "justification": "Sorting first is an improvement over brute force but slower than a set-based check.",
    },
    {
        "id": "check_duplicates_optimal",
        "problem": "Check for Duplicates",
        "code": """
def has_duplicates(nums):
    return len(set(nums)) != len(nums)
""",
        "true_big_o": "O(N)",
        "efficiency_score": 5,
        "style_score": 5,
        "justification": "Optimal set-based approach, clean and idiomatic.",
    },
]
