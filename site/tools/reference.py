"""One Function finder entry per built-in function and method, next to the task-style recipes in build_learn.py.

Each entry is (name, what it does, example code, one-line note). build_learn.py runs every example with real
Python, so the output shown on the site is exactly what it prints.
"""

CATEGORIES = [
    {"id": "ref-builtins", "glyph": "len()", "title": "Every built-in function", "blurb": "The functions that are always there, no import needed. One entry each."},
    {"id": "ref-str", "glyph": "s.x()", "title": "Every string method", "blurb": "Everything you can call on text, from .capitalize() to .zfill(). One entry each."},
    {"id": "ref-list", "glyph": "l.x()", "title": "Every list method", "blurb": "All eleven list methods, one entry each."},
    {"id": "ref-dict", "glyph": "d.x()", "title": "Every dict and set method", "blurb": "Dictionary and set methods, one entry each."},
    {"id": "ref-modules", "glyph": "import", "title": "math, random and statistics", "blurb": "The standard-library functions school problems use most."},
]

# The lesson that teaches each kind of thing, so every entry links back into the levels.
LESSON = {"ref-str": "level-2", "ref-list": "level-4", "ref-dict": "level-5", "ref-modules": "level-8"}

R = {c["id"]: [] for c in CATEGORIES}


def ref(cat, name, what, code, note=""):
    R[cat].append((name, what, code.strip("\n"), note))


# ---------------------------------------------------------------- built-in functions
B = "ref-builtins"
ref(B, "abs()", "distance from zero", 'print(abs(-7), abs(3.5))', "Always 0 or positive.")
ref(B, "all()", "is every item true?", 'print(all([True, 1, "x"]))\nprint(all(n > 0 for n in [3, -1, 5]))', "An empty list gives True.")
ref(B, "any()", "is at least one item true?", 'print(any(c.isdigit() for c in "abc1"))\nprint(any([]))', "An empty list gives False.")
ref(B, "bin()", "number to binary text", 'print(bin(10))\nprint(bin(10)[2:])', "[2:] cuts off the 0b prefix.")
ref(B, "bool()", "true or false?", 'print(bool(0), bool(""), bool([]), bool("0"), bool(5))', "0, empty and None are False; everything else is True.")
ref(B, "chr()", "number to character", 'print(chr(65), chr(97), chr(48))', "The opposite of ord().")
ref(B, "dict()", "make a dictionary", 'print(dict(a=1, b=2))\nprint(dict([("x", 1), ("y", 2)]))\nprint(dict(zip("ab", [1, 2])))')
ref(B, "divmod()", "whole division and remainder together", 'minutes, seconds = divmod(135, 60)\nprint(minutes, seconds)', "Same as (a // b, a % b).")
ref(B, "enumerate()", "loop with a counter", 'for i, fruit in enumerate(["apple", "pear"], start=1):\n    print(i, fruit)')
ref(B, "filter()", "keep the items a test says yes to", 'evens = list(filter(lambda n: n % 2 == 0, [1, 2, 3, 4]))\nprint(evens)', "A comprehension does the same: [n for n in nums if n % 2 == 0].")
ref(B, "float()", "text or whole number to a decimal", 'print(float("3.5"), float(7), float("  2 "))', "Spaces at the ends are fine; letters give a ValueError.")
ref(B, "format()", "format one value", 'print(format(3.14159, ".2f"))\nprint(format(1234567, ","))', "The same codes work inside f-strings: f\"{x:.2f}\".")
ref(B, "hex()", "number to hexadecimal text", 'print(hex(255))\nprint(int("ff", 16))', "int(text, 16) goes back.")
ref(B, "input()", "read one line typed by the user", '# name = input("Name? ")    # waits for Enter, gives back TEXT\nname = "Sam"                 # (what it would return)\nprint(type(name))', "Always a string: use int(input()) for a number.")
ref(B, "int()", "text or decimal to a whole number", 'print(int("42"), int(7.9), int("-3"))\nprint(int("101", 2), int("0x1f", 0))', "int(7.9) cuts off the decimals, it doesn't round.")
ref(B, "isinstance()", "is this value of that type?", 'print(isinstance(5, int))\nprint(isinstance("5", (int, float)))')
ref(B, "len()", "how many items or characters", 'print(len("hello"), len([1, 2, 3]), len({"a": 1}))')
ref(B, "list()", "make a list", 'print(list("abc"))\nprint(list(range(4)))\nprint(list({"x": 1, "y": 2}))', "From a dict you get its keys.")
ref(B, "map()", "do the same thing to every item", 'numbers = list(map(int, "3 4 5".split()))\nprint(numbers)', "map(int, ...) is the quick way to turn a line of numbers into a list.")
ref(B, "max()", "the biggest item", 'print(max(3, 9, 2))\nprint(max(["pear", "fig", "banana"], key=len))', "key= says what to compare by.")
ref(B, "min()", "the smallest item", 'print(min([4, 1, 8]))\nprint(min("hello"))\nprint(min([], default=0))', "default= avoids an error on an empty list.")
ref(B, "oct()", "number to octal text", 'print(oct(8))')
ref(B, "ord()", "character to number", 'print(ord("A"), ord("a"), ord("0"))', "The opposite of chr().")
ref(B, "pow()", "power, optionally with a remainder", 'print(pow(2, 10))\nprint(pow(2, 10, 1000))', "pow(a, b) is the same as a ** b.")
ref(B, "print()", "show values on screen", 'print("a", "b", 3)\nprint("a", "b", sep="-")\nprint("no new line", end="!\\n")')
ref(B, "range()", "a run of whole numbers", 'print(list(range(5)))\nprint(list(range(2, 8, 2)))\nprint(list(range(5, 0, -1)))', "The end number is never included.")
ref(B, "reversed()", "the items back to front", 'print(list(reversed([1, 2, 3])))\nprint("".join(reversed("abc")))')
ref(B, "round()", "round a number", 'print(round(3.14159, 2), round(2.5), round(3.5), round(1234, -2))', "Halves go to the nearest even number: round(2.5) is 2.")
ref(B, "set()", "make a set (no duplicates)", 'print(sorted(set([3, 1, 3, 2, 1])))\nprint(set())', "set() is the empty set; {} is an empty dict.")
ref(B, "sorted()", "a new sorted list", 'print(sorted([3, 1, 2]))\nprint(sorted(["b", "A", "c"], key=str.lower))\nprint(sorted([3, 1, 2], reverse=True))', "Leaves the original alone, unlike .sort().")
ref(B, "str()", "anything to text", 'print(str(42) + "!", str(3.0), str([1, 2]))')
ref(B, "sum()", "add up all the items", 'print(sum([1, 2, 3]))\nprint(sum(n * n for n in range(4)))')
ref(B, "tuple()", "make a tuple", 'print(tuple([1, 2]))\nprint(tuple("hi"))')
ref(B, "type()", "what type is this?", 'print(type(5), type("5"), type(5.0), type([5]))', "Handy when a value isn't what you expect.")
ref(B, "zip()", "walk through several lists together", 'for name, score in zip(["Ann", "Bo"], [90, 75]):\n    print(name, score)', "Stops at the shortest list.")

# ---------------------------------------------------------------- string methods
S = "ref-str"
ref(S, ".capitalize()", "first letter capital, the rest small", 'print("hELLO world".capitalize())')
ref(S, ".casefold()", "lowercase for comparing", 'print("Straße".casefold() == "STRASSE".casefold())', "Stronger than .lower() for comparing words.")
ref(S, ".center()", "pad text to sit in the middle", 'print("[" + "hi".center(8) + "]")\nprint("hi".center(8, "*"))')
ref(S, ".count()", "how many times something appears", 'print("banana".count("a"))\nprint("banana".count("an"))', "Overlapping matches aren't counted twice.")
ref(S, ".endswith()", "check how the text ends", 'filename = "report.pdf"\nprint(filename.endswith(".pdf"))\nprint(filename.endswith((".jpg", ".png")))\nprint("123m".endswith("m"))', "Give a tuple to check several endings at once.")
ref(S, ".find()", "position of something, or -1", 'print("hello".find("l"))\nprint("hello".find("z"))', "Use .find() when it might be missing; .index() raises an error instead.")
ref(S, ".format()", "fill {} in a template", 'print("{} is {} years old".format("Sam", 25))\nprint("{:.2f}".format(3.14159))', "f-strings do the same and are easier to read.")
ref(S, ".index()", "position of something, or an error", 'print("hello".index("e"))', "ValueError if it isn't there.")
ref(S, ".isalnum()", "only letters and digits?", 'print("abc123".isalnum(), "abc 123".isalnum())')
ref(S, ".isalpha()", "only letters?", 'print("hello".isalpha(), "hello1".isalpha(), "".isalpha())', "An empty string gives False.")
ref(S, ".isdecimal()", "only 0-9 digits?", 'print("123".isdecimal(), "-1".isdecimal(), "1.5".isdecimal())', "Minus signs and points make it False: use try/int() for real numbers.")
ref(S, ".isdigit()", "only digits?", 'print("2024".isdigit(), "20 24".isdigit(), "-5".isdigit())', "Like .isdecimal(), but also accepts things like '²'.")
ref(S, ".islower()", "all letters lowercase?", 'print("hello".islower(), "Hello".islower())')
ref(S, ".isnumeric()", "only number characters?", 'print("123".isnumeric(), "½".isnumeric(), "1.5".isnumeric())')
ref(S, ".isspace()", "only spaces, tabs or new lines?", 'print("   ".isspace(), " a ".isspace())')
ref(S, ".istitle()", "every word capitalised?", 'print("Hello World".istitle(), "Hello world".istitle())')
ref(S, ".isupper()", "all letters capitals?", 'print("ABC".isupper(), "AbC".isupper())')
ref(S, ".join()", "glue a list of text together", 'print("-".join(["a", "b", "c"]))\nprint("".join(["h", "i"]))\nprint(", ".join(str(n) for n in [1, 2, 3]))', "Every item must already be text.")
ref(S, ".ljust()", "pad on the right (text sits left)", 'print("[" + "hi".ljust(6) + "]")\nprint("7".ljust(3, "0"))')
ref(S, ".lower()", "all lowercase", 'print("HeLLo".lower())\nprint("YES".lower() == "yes")', "Compare answers in lowercase so 'Yes' and 'yes' both match.")
ref(S, ".lstrip()", "remove characters from the left", 'print("   hi  ".lstrip() + "|")\nprint("0042".lstrip("0"))')
ref(S, ".partition()", "split once into before, separator, after", 'print("key=value=x".partition("="))\nprint("no sep".partition("="))')
ref(S, ".removeprefix()", "remove text from the start, if it's there", 'print("Mr Smith".removeprefix("Mr "))\nprint("Smith".removeprefix("Mr "))')
ref(S, ".removesuffix()", "remove text from the end, if it's there", 'print("123m".removesuffix("m"))\nprint("report.pdf".removesuffix(".pdf"))', "Pairs well with .endswith().")
ref(S, ".replace()", "swap one piece of text for another", 'print("a-b-c".replace("-", " "))\nprint("a-b-c".replace("-", "", 1))', "The 3rd argument limits how many get replaced.")
ref(S, ".rfind()", "last position of something, or -1", 'print("a.b.c".rfind("."))')
ref(S, ".rindex()", "last position of something, or an error", 'print("hello".rindex("l"))')
ref(S, ".rjust()", "pad on the left (text sits right)", 'print("[" + "42".rjust(5) + "]")\nprint("7".rjust(3, "0"))')
ref(S, ".rsplit()", "split, counting from the right", 'print("a.b.c.pdf".rsplit(".", 1))', "rsplit('.', 1) separates a file extension.")
ref(S, ".rstrip()", "remove characters from the right", 'print("hi\\n".rstrip() + "|")\nprint("99.50ft".rstrip("ft"))', "It removes any of the given characters, not the exact word.")
ref(S, ".split()", "cut text into a list", 'print("a b  c".split())\nprint("a,b,,c".split(","))\nprint("1 2 3".split(maxsplit=1))', "With no argument it splits on any run of spaces.")
ref(S, ".splitlines()", "one list item per line", 'print("one\\ntwo\\nthree".splitlines())')
ref(S, ".startswith()", "check how the text starts", 'print("hello".startswith("he"))\nprint("0x1f".startswith(("0x", "0b")))', "Give a tuple to check several starts at once.")
ref(S, ".strip()", "remove spaces (or other characters) from both ends", 'print("  hi  ".strip() + "|")\nprint("--hi--".strip("-"))')
ref(S, ".swapcase()", "capitals become small and small become capitals", 'print("Hello".swapcase())')
ref(S, ".title()", "Every Word Capitalised", 'print("the cat sat".title())')
ref(S, ".upper()", "ALL CAPITALS", 'print("hello".upper())')
ref(S, ".zfill()", "pad with zeros on the left", 'print("7".zfill(3), "-5".zfill(4))', "Keeps a minus sign in front.")

# ---------------------------------------------------------------- list methods
L = "ref-list"
ref(L, ".append()", "add one item to the end", 'nums = [1, 2]\nnums.append(3)\nprint(nums)', "Returns None: don't write nums = nums.append(3).")
ref(L, ".clear()", "remove everything", 'nums = [1, 2, 3]\nnums.clear()\nprint(nums)')
ref(L, ".copy()", "a separate copy of the list", 'a = [1, 2]\nb = a.copy()\nb.append(3)\nprint(a, b)', "b = a would NOT copy: both names would share one list.")
ref(L, ".count()", "how many times a value appears", 'print([1, 2, 2, 3, 2].count(2))')
ref(L, ".extend()", "add several items to the end", 'nums = [1]\nnums.extend([2, 3])\nprint(nums)', "append([2, 3]) would add one item that is itself a list.")
ref(L, ".index()", "position of a value", 'print(["a", "b", "c"].index("b"))', "ValueError if it isn't in the list: check with `in` first.")
ref(L, ".insert()", "add an item at a position", 'nums = [1, 3]\nnums.insert(1, 2)\nprint(nums)')
ref(L, ".pop()", "take an item out and get it back", 'nums = [10, 20, 30]\nprint(nums.pop(), nums)\nprint(nums.pop(0), nums)', "No argument means the last item.")
ref(L, ".remove()", "remove the first matching value", 'nums = [1, 2, 1]\nnums.remove(1)\nprint(nums)', "Removes by value; del nums[i] removes by position.")
ref(L, ".reverse()", "flip the list in place", 'nums = [1, 2, 3]\nnums.reverse()\nprint(nums)', "nums[::-1] gives a reversed copy instead.")
ref(L, ".sort()", "sort the list in place", 'nums = [3, 1, 2]\nnums.sort()\nprint(nums)\nwords = ["bb", "a", "ccc"]\nwords.sort(key=len, reverse=True)\nprint(words)', "Returns None; sorted(nums) gives a new list instead.")

# ---------------------------------------------------------------- dict and set methods
D = "ref-dict"
ref(D, "dict .get()", "read a key, with a fallback", 'ages = {"Sam": 25}\nprint(ages.get("Sam"), ages.get("Ann"), ages.get("Ann", 0))', "No KeyError: counts[w] = counts.get(w, 0) + 1 is the counting pattern.")
ref(D, "dict .items()", "loop over keys and values", 'for name, age in {"Sam": 25, "Ann": 31}.items():\n    print(name, age)')
ref(D, "dict .keys()", "all the keys", 'print(list({"a": 1, "b": 2}.keys()))', "Looping over a dict gives the keys anyway.")
ref(D, "dict .values()", "all the values", 'print(sum({"a": 1, "b": 2}.values()))')
ref(D, "dict .pop()", "remove a key and get its value", 'd = {"a": 1, "b": 2}\nprint(d.pop("a"), d)\nprint(d.pop("z", None))')
ref(D, "dict .popitem()", "remove the last added pair", 'd = {"a": 1, "b": 2}\nprint(d.popitem(), d)')
ref(D, "dict .setdefault()", "get a key, adding it first if missing", 'groups = {}\ngroups.setdefault("fruit", []).append("apple")\nprint(groups)')
ref(D, "dict .update()", "add or overwrite several pairs", 'd = {"a": 1}\nd.update({"a": 9, "b": 2})\nprint(d)')
ref(D, "dict .copy()", "a separate copy of the dictionary", 'a = {"x": 1}\nb = a.copy()\nb["x"] = 2\nprint(a, b)')
ref(D, "dict .clear()", "remove every pair", 'd = {"a": 1}\nd.clear()\nprint(d)')
ref(D, "dict.fromkeys()", "a dictionary with every key set to one value", 'print(dict.fromkeys(["a", "b"], 0))')
ref(D, "set .add()", "add one item", 's = {1, 2}\ns.add(2)\ns.add(3)\nprint(s)', "Adding something already there changes nothing.")
ref(D, "set .discard()", "remove an item if it's there", 's = {1, 2}\ns.discard(5)\ns.discard(1)\nprint(s)', ".remove() raises a KeyError when it's missing; .discard() doesn't.")
ref(D, "set .remove()", "remove an item (error if missing)", 's = {1, 2}\ns.remove(1)\nprint(s)')
ref(D, "set .union()", "everything in either set", 'print(sorted({1, 2}.union({2, 3})))', "Same as a | b.")
ref(D, "set .intersection()", "only what both sets have", 'print({1, 2, 3}.intersection({2, 3, 4}))', "Same as a & b.")
ref(D, "set .difference()", "what's in the first but not the second", 'print({1, 2, 3}.difference({2}))', "Same as a - b.")
ref(D, "set .symmetric_difference()", "what's in exactly one of them", 'print(sorted({1, 2, 3}.symmetric_difference({3, 4})))', "Same as a ^ b.")
ref(D, "set .issubset()", "is every item also in the other set?", 'print({1, 2}.issubset({1, 2, 3}))', "Same as a <= b.")
ref(D, "set .issuperset()", "does it contain every item of the other?", 'print({1, 2, 3}.issuperset({2, 3}))')
ref(D, "set .isdisjoint()", "do they share nothing?", 'print({1, 2}.isdisjoint({3, 4}))')

# ---------------------------------------------------------------- modules
M = "ref-modules"
ref(M, "math.sqrt()", "square root", 'import math\nprint(math.sqrt(16), math.sqrt(2))')
ref(M, "math.isqrt()", "whole-number square root", 'import math\nprint(math.isqrt(17))', "Exact for huge numbers; handy for checking primes up to the root.")
ref(M, "math.ceil()", "round up", 'import math\nprint(math.ceil(2.1), math.ceil(-2.1))')
ref(M, "math.floor()", "round down", 'import math\nprint(math.floor(2.9), math.floor(-2.1))')
ref(M, "math.pi", "the number pi", 'import math\nprint(math.pi)\nprint(round(math.pi * 3 ** 2, 2))')
ref(M, "math.gcd()", "greatest common divisor", 'import math\nprint(math.gcd(12, 18))')
ref(M, "math.lcm()", "lowest common multiple", 'import math\nprint(math.lcm(4, 6))')
ref(M, "math.factorial()", "n! = 1 x 2 x ... x n", 'import math\nprint(math.factorial(5))')
ref(M, "math.log()", "logarithm", 'import math\nprint(math.log(8, 2), math.log10(1000))')
ref(M, "math.fabs() and math.trunc()", "absolute value as a float; cut off decimals", 'import math\nprint(math.fabs(-3), math.trunc(-3.7))')
ref(M, "random.randint()", "a random whole number, both ends included", 'import random\nrandom.seed(1)               # same "random" numbers every run, so the output matches\nprint(random.randint(1, 6))')
ref(M, "random.choice()", "one random item", 'import random\nrandom.seed(1)\nprint(random.choice(["rock", "paper", "scissors"]))')
ref(M, "random.shuffle()", "mix a list in place", 'import random\nrandom.seed(1)\ncards = [1, 2, 3, 4]\nrandom.shuffle(cards)\nprint(cards)')
ref(M, "random.sample()", "several different random items", 'import random\nrandom.seed(1)\nprint(random.sample(range(1, 50), 3))')
ref(M, "random.random() and random.uniform()", "a random decimal", 'import random\nrandom.seed(1)\nprint(round(random.random(), 3), round(random.uniform(5, 10), 3))')
ref(M, "statistics.mean()", "average", 'import statistics\nprint(statistics.mean([2, 4, 9]))')
ref(M, "statistics.median()", "middle value", 'import statistics\nprint(statistics.median([7, 1, 3]), statistics.median([1, 2, 3, 4]))')
ref(M, "statistics.mode()", "most common value", 'import statistics\nprint(statistics.mode([1, 2, 2, 3]))')
ref(M, "statistics.stdev()", "how spread out the values are", 'import statistics\nprint(round(statistics.stdev([2, 4, 4, 4, 5, 5, 7, 9]), 3))')
