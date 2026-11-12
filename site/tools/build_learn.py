"""Build the Learn page data.

1. Lessons: cut "Python Refresher and Projects.html" (next to the site folder) into one
   entry per level, give every heading an id, and make a search entry per heading.
2. Function finder: the RECIPES below. Each one is run with real Python here, so the
   output shown on the site is exactly what the code prints.

Run:  py site/tools/build_learn.py   ->  writes js/lessons.js and js/learn-index.js
"""
import ast
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_problems import FILES, P as PROBLEMS, run  # same sandboxed runner and data files as the problems

sys.path.insert(0, str(Path(__file__).parent.parent))
import mistakes  # site/mistakes.py: its links into the lessons are checked below

SITE = Path(__file__).resolve().parent.parent
SRC = SITE.parent / "Python Refresher and Projects.html"

# ---------------------------------------------------------------- function finder

CATEGORIES = [
    {"id": "convert", "glyph": 'int("7")', "title": "Converting between types", "blurb": "Text to number, letter to number, list to text, and back."},
    {"id": "text", "glyph": '"abc"', "title": "Strings and letters", "blurb": "Slicing, cleaning, searching and checking text."},
    {"id": "numbers", "glyph": '7 % 2', "title": "Numbers and maths", "blurb": "Rounding, remainders, digits, primes and the math module."},
    {"id": "lists", "glyph": '[ ]', "title": "Lists", "blurb": "Adding, removing, sorting, filtering and looping."},
    {"id": "dicts", "glyph": '{k: v}', "title": "Dictionaries and sets", "blurb": "Counting, looking things up and removing duplicates."},
    {"id": "loops", "glyph": 'for', "title": "Loops and functions", "blurb": "range, while, break, enumerate, zip and recursion."},
    {"id": "files", "glyph": 'open()', "title": "Files, CSV and JSON", "blurb": "Reading, writing and skipping broken lines."},
    {"id": "dates", "glyph": '12:30', "title": "Dates and times", "blurb": "Parsing, formatting and the gap between two dates."},
    {"id": "errors", "glyph": 'except', "title": "Errors and checking input", "blurb": "try/except, ValueError and asking again."},
    {"id": "print", "glyph": 'f"{x}"', "title": "Printing and formatting", "blurb": "f-strings, decimals, padding and print options."},
]

RECIPES = []


def recipe(id, cat, title, code, keys="", note="", files=(), lesson=""):
    RECIPES.append({"id": id, "cat": cat, "title": title, "keys": keys, "code": code.strip("\n"),
                    "note": note, "files": list(files), "lesson": lesson})


# Converting
recipe("letter-to-number", "convert", "Letter to number: ord()", '''
print(ord("A"))
print(ord("a"))
print(ord("!"))
''', keys="convert character char letters to numbers code ascii unicode value",
    note="Every character has a number (its Unicode code). Capitals A-Z are 65-90, small a-z are 97-122.", lesson="level-2")
recipe("number-to-letter", "convert", "Number to letter: chr()", '''
print(chr(65))
print(chr(97))
print(chr(ord("a") + 2))
''', keys="convert numbers to letters character char code ascii unicode", note="chr() is the opposite of ord().")
recipe("alphabet-position", "convert", "Letter's place in the alphabet (a = 1)", '''
letter = "d"
position = ord(letter.lower()) - ord("a") + 1
print(position)

word = "abc"
print([ord(c) - ord("a") + 1 for c in word])
''', keys="convert letters to numbers alphabet position index a=1 b=2 word to numbers")
recipe("position-to-letter", "convert", "Place in the alphabet to letter (1 = a)", '''
n = 4
print(chr(ord("a") + n - 1))
print("".join(chr(ord("a") + n - 1) for n in [8, 9]))
''', keys="convert numbers to letters alphabet position")
recipe("str-to-int", "convert", "Text to a whole number or decimal: int(), float()", '''
age = int("42")
price = float("3.50")
print(age + 1, price * 2)
''', keys="convert string str text input to int integer number float decimal parse cast", lesson="level-1")
recipe("int-to-str", "convert", "Number to text: str()", '''
count = 7
message = "You have " + str(count) + " messages"
print(message)
print(len(str(12345)), "digits")
''', keys="convert int integer number to string str text concatenate")
recipe("str-to-list", "convert", "Text to a list of letters or words", '''
print(list("hello"))
print("one two three".split())
print("a,b,c".split(","))
''', keys="convert string to list characters letters split words")
recipe("list-to-str", "convert", "List to text: join()", '''
words = ["red", "green", "blue"]
print(", ".join(words))
print("".join(["a", "b", "c"]))
numbers = [1, 2, 3]
print(" ".join(str(n) for n in numbers))
''', keys="convert list to string join combine glue", note="join() only accepts text, so convert numbers with str() first.")
recipe("int-to-base", "convert", "Number to binary, hex or any base", '''
print(bin(10), hex(255), oct(8))
print(format(10, "b"), format(255, "x"))
print(int("1010", 2), int("ff", 16))
''', keys="convert binary hexadecimal octal base 2 16 radix")
recipe("float-to-int", "convert", "Decimal to whole number: int(), round()", '''
print(int(3.9))
print(round(3.9))
print(round(2.5), round(3.5))
''', keys="convert float decimal to int integer truncate round chop",
    note="int() just cuts off the decimals. round() goes to the nearest even number on a tie (2.5 becomes 2).")
recipe("bool-convert", "convert", "Which values count as False", '''
print(bool(0), bool(""), bool([]), bool(None))
print(bool(5), bool("no"), bool([0]))
''', keys="convert bool boolean truthy falsy empty")
recipe("tuple-list-set", "convert", "Switch between list, tuple and set", '''
items = [3, 1, 3, 2]
print(tuple(items))
print(set(items))
print(sorted(set(items)))
''', keys="convert list tuple set")
recipe("money-text", "convert", 'Text like "$300 K" to a number', '''
endorsement = "$300 K"
amount = float(endorsement.replace("$", "").replace("K", "").strip()) * 1000
print(amount)

price = "12.50 EUR"
print(float(price[:-4]))
''', keys="convert currency money dollars string to number strip remove symbol thousand million")

# Strings and letters
recipe("change-case", "text", "Upper, lower and title case", '''
name = "ada lovelace"
print(name.upper())
print(name.title())
print("MiXeD".lower(), "hi".capitalize(), "Hi".swapcase())
''', keys="capital uppercase lowercase capitalize", lesson="level-2")
recipe("strip", "text", "Remove spaces at the ends: strip()", '''
raw = "   hello  \\n"
print(repr(raw.strip()))
print(repr(raw.lstrip()), repr(raw.rstrip()))
print("--hi--".strip("-"))
''', keys="trim whitespace newline remove spaces clean", lesson="level-2")
recipe("split-words", "text", "Split text into words or parts", '''
sentence = "the quick  brown fox"
print(sentence.split())
print("12:30:05".split(":"))
first, last = "Ada Lovelace".split()
print(last)
''', keys="split words tokens separate break apart colon comma")
recipe("reverse-string", "text", "Reverse a string", '''
word = "python"
print(word[::-1])
print("".join(reversed(word)))
''', keys="reverse backwards flip string text")
recipe("palindrome", "text", "Check for a palindrome", '''
word = "Racecar"
cleaned = word.lower()
print(cleaned == cleaned[::-1])
print(str(12321) == str(12321)[::-1])
''', keys="palindrome same backwards reverse check")
recipe("slice", "text", "Slice: first, last and middle characters", '''
text = "Hello, world"
print(text[0], text[-1])
print(text[:5])
print(text[-5:])
print(text[7:10])
print(text[::2])
''', keys="slice substring first last characters index part cut", lesson="level-2",
    note="text[a:b] stops before b. text[-3:] is the last 3 characters.")
recipe("find", "text", "Find where something is: find(), index()", '''
text = "banana"
print(text.find("n"))
print(text.find("z"))
print(text.rfind("a"))
print("nan" in text)
''', keys="search find position index substring contains locate")
recipe("count-substring", "text", "Count how often something appears", '''
text = "banana"
print(text.count("a"))
print(text.count("an"))
vowels = sum(1 for c in "programming" if c in "aeiou")
print(vowels)
''', keys="count occurrences vowels letters how many")
recipe("replace", "text", "Replace or remove part of a string", '''
text = "I like cats. cats are great."
print(text.replace("cats", "dogs"))
print(text.replace("cats", "dogs", 1))
print("1,000,000".replace(",", ""))
''', keys="replace substitute remove delete change characters")
recipe("char-checks", "text", "Is it a digit, letter, capital or space?", '''
for c in "a7 B":
    print(repr(c), c.isalpha(), c.isdigit(), c.isupper(), c.isspace())
print("abc123".isalnum(), "42".isdigit(), "-42".isdigit())
''', keys="isdigit isalpha isupper islower isspace isalnum check character type number letter")
recipe("keep-letters", "text", "Keep only the letters (remove digits and punctuation)", '''
text = "Hi! It's 9am."
print("".join(c for c in text if c.isalpha()))
print("".join(c for c in text if c.isalnum() or c == " "))
''', keys="remove punctuation digits filter characters clean only letters")
recipe("starts-ends", "text", "Starts with, ends with, file extension", '''
filename = "report.final.pdf"
print(filename.endswith(".pdf"))
print(filename.startswith("rep"))
print(filename.rsplit(".", 1)[-1])
''', keys="startswith endswith prefix suffix file extension type")
recipe("alphabet", "text", "The whole alphabet and digits", '''
import string
print(string.ascii_lowercase)
print(string.ascii_uppercase)
print(string.digits)
print(string.punctuation)
''', keys="alphabet letters a-z all letters string module")
recipe("caesar-shift", "text", "Shift a letter around the alphabet (Caesar cipher)", '''
def shift(c, n):
    if c.isupper():
        return chr((ord(c) - ord("A") + n) % 26 + ord("A"))
    if c.islower():
        return chr((ord(c) - ord("a") + n) % 26 + ord("a"))
    return c

print("".join(shift(c, 3) for c in "Hello, xyz!"))
print("".join(shift(c, -3) for c in "Khoor"))
''', keys="caesar cipher shift encrypt decrypt rotate letters ord chr wrap modulo % 26")
recipe("repeat-text", "text", "Repeat text, check length", '''
print("-" * 20)
print("ab" * 3)
print(len("hello"))
''', keys="repeat multiply length len line divider")
recipe("multiline", "text", "Text over several lines", '''
poem = """Roses are red,
violets are blue."""
print(poem)
print(poem.splitlines())
''', keys="multiline triple quotes newline lines splitlines")

# Numbers and maths
recipe("div-mod", "numbers", "Whole division and remainder: //, %, divmod()", '''
print(17 // 5, 17 % 5)
print(divmod(17, 5))
minutes = 135
hours, mins = divmod(minutes, 60)
print(f"{hours}h {mins}min")
''', keys="integer division floor remainder modulo divmod quotient hours minutes", lesson="level-1")
recipe("even-odd", "numbers", "Even or odd, divisible by", '''
n = 14
print(n % 2 == 0)
print(n % 7 == 0)
''', keys="even odd divisible multiple modulo remainder check")
recipe("round", "numbers", "Round to 2 decimals", '''
x = 3.14159
print(round(x, 2))
print(f"{x:.2f}")
print(f"{2.5:.2f}")
''', keys="round decimals places precision money 2dp",
    note="round() gives a number; f\"{x:.2f}\" gives text that always shows 2 decimals (2.50, not 2.5).")
recipe("ceil-floor", "numbers", "Round up or down: math.ceil, math.floor", '''
import math
print(math.ceil(4.1), math.floor(4.9))
print(math.ceil(-4.1), math.floor(-4.1))
''', keys="round up down ceiling floor math")
recipe("power-root", "numbers", "Powers and square roots", '''
import math
print(2 ** 10)
print(math.sqrt(16))
print(27 ** (1 / 3))
print(math.isqrt(17))
''', keys="power exponent square root sqrt cube math")
recipe("abs-min-max", "numbers", "Absolute value, smallest, biggest", '''
print(abs(-7))
print(min(4, 9, 2), max(4, 9, 2))
print(max([3, 8, 1]))
''', keys="absolute abs minimum maximum smallest biggest largest number list")
recipe("sum-average", "numbers", "Sum and average", '''
scores = [70, 85, 90]
print(sum(scores))
print(sum(scores) / len(scores))
print(f"{sum(scores) / len(scores):.1f}")
''', keys="sum total average mean list numbers", lesson="level-4")
recipe("digits", "numbers", "Digits of a number, digit sum", '''
n = 4096
digits = [int(d) for d in str(n)]
print(digits)
print(sum(digits))
print(len(str(n)))
''', keys="digits split number sum of digits digital root count digits")
recipe("is-prime", "numbers", "Is it a prime number?", '''
def is_prime(n):
    if n < 2:
        return False
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            return False
    return True

print([n for n in range(1, 30) if is_prime(n)])
''', keys="prime number check divisor factor square root")
recipe("prime-factors", "numbers", "Prime factors of a number", '''
n = 360
factors = []
d = 2
while n > 1:
    while n % d == 0:
        factors.append(d)
        n //= d
    d += 1
print(factors)
''', keys="prime factors factorization factorise divide while")
recipe("gcd-factorial", "numbers", "Factorial, greatest common divisor", '''
import math
print(math.factorial(5))
print(math.gcd(12, 18))
print(math.lcm(4, 6))
''', keys="factorial gcd greatest common divisor lcm math")
recipe("random", "numbers", "Random numbers and choices", '''
import random
random.seed(1)  # same "random" numbers every run, handy for testing
print(random.randint(1, 6))
print(random.choice(["rock", "paper", "scissors"]))
print(random.random() < 1)
''', keys="random dice randint choice shuffle", note="Without random.seed() you get different numbers each run.", lesson="level-8")
recipe("percent", "numbers", "Percentages and growth", '''
old, new = 200, 230
change = (new - old) / old * 100
print(f"{change:.1f}%")
print(f"{0.256:.1%}")
print(f"{5 / 1000 * 1000:.1f} per mille")
''', keys="percent percentage per mille growth increase change rate")
recipe("float-close", "numbers", "Why 0.1 + 0.2 isn't 0.3", '''
import math
print(0.1 + 0.2)
print(0.1 + 0.2 == 0.3)
print(math.isclose(0.1 + 0.2, 0.3))
''', keys="float precision compare equal isclose decimal error")

# Lists
recipe("list-add", "lists", "Add items: append, insert, extend", '''
items = ["a", "b"]
items.append("c")
items.insert(0, "start")
items.extend(["x", "y"])
print(items)
''', keys="add append insert extend push list", lesson="level-4")
recipe("list-remove", "lists", "Remove items: remove, pop, del", '''
items = ["a", "b", "c", "d"]
items.remove("b")
last = items.pop()
del items[0]
print(items, last)
''', keys="remove delete pop del list item")
recipe("sort", "lists", "Sort a list", '''
nums = [5, 2, 9, 1]
print(sorted(nums))
print(sorted(nums, reverse=True))
words = ["pear", "fig", "banana"]
print(sorted(words, key=len))
nums.sort()
print(nums)
''', keys="sort order ascending descending reverse key sorted", lesson="level-4",
    note="sorted() makes a new list. list.sort() changes the list and returns None, so never write nums = nums.sort().")
recipe("sort-by", "lists", "Sort rows by a column", '''
people = [("Ada", 36), ("Linus", 21), ("Grace", 85)]
print(sorted(people, key=lambda p: p[1]))
print(sorted(people, key=lambda p: p[1], reverse=True)[0])
''', keys="sort by column key lambda tuple field age oldest")
recipe("reverse-list", "lists", "Reverse a list", '''
items = [1, 2, 3]
print(items[::-1])
print(list(reversed(items)))
''', keys="reverse backwards flip list")
recipe("dedupe", "lists", "Remove duplicates", '''
items = [3, 1, 3, 2, 1]
print(list(set(items)))
print(list(dict.fromkeys(items)))
print(len(set(items)), "unique")
''', keys="remove duplicates unique distinct set", note="set() loses the order; dict.fromkeys() keeps it.", lesson="level-5")
recipe("second-largest", "lists", "Second largest value", '''
nums = [4, 9, 2, 9, 7]
print(sorted(set(nums))[-2])
''', keys="second largest biggest max runner up")
recipe("index-count", "lists", "Position of an item, how many times", '''
items = ["a", "b", "a"]
print(items.index("b"))
print(items.count("a"))
print("c" in items)
''', keys="index position find count contains in list")
recipe("filter-map", "lists", "Filter or change every item (list comprehension)", '''
nums = [3, -1, 4, -5, 9]
print([n for n in nums if n > 0])
print([n * 2 for n in nums])
print([w.upper() for w in ["a", "b"]])
''', keys="filter map transform comprehension keep only each item", lesson="level-4")
recipe("min-max-key", "lists", "Longest word, item with the biggest value", '''
words = ["fig", "banana", "kiwi"]
print(max(words, key=len))
print(min(words, key=len))
''', keys="longest shortest max min key len")
recipe("first-last", "lists", "First, last and a slice of a list", '''
items = [10, 20, 30, 40, 50]
print(items[0], items[-1])
print(items[:2], items[-2:])
print(len(items))
''', keys="first last element slice length list")
recipe("empty-check", "lists", "Check if a list is empty", '''
items = []
if not items:
    print("empty")
print(len(items) == 0)
''', keys="empty list check len zero none")
recipe("nested", "lists", "List of lists (a grid)", '''
grid = [[1, 2, 3], [4, 5, 6]]
print(grid[1][2])
for row in grid:
    print(" ".join(str(n) for n in row))
print([n for row in grid for n in row])
''', keys="nested list 2d grid matrix table flatten")

# Dictionaries and sets
recipe("count-things", "dicts", "Count things with a dictionary", '''
counts = {}
for word in "the cat and the hat".split():
    counts[word] = counts.get(word, 0) + 1
print(counts)

from collections import Counter
print(Counter("banana").most_common(2))
''', keys="count frequency occurrences tally dictionary get Counter most common", lesson="level-5")
recipe("dict-basics", "dicts", "Make, read and change a dictionary", '''
ages = {"Ada": 36, "Linus": 21}
ages["Grace"] = 85
ages["Ada"] += 1
print(ages["Ada"])
print(ages.get("Bob", "unknown"))
del ages["Linus"]
print(ages)
''', keys="dictionary dict key value add update get missing key lookup", lesson="level-5")
recipe("dict-loop", "dicts", "Loop over keys and values", '''
prices = {"apple": 0.5, "pear": 0.75}
for name, price in prices.items():
    print(f"{name}: {price:.2f}")
print(list(prices.keys()), list(prices.values()))
''', keys="loop dictionary items keys values iterate")
recipe("sort-dict", "dicts", "Sort a dictionary by value", '''
scores = {"Ada": 82, "Linus": 95, "Grace": 77}
for name, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
    print(name, score)
print(max(scores, key=scores.get))
''', keys="sort dictionary by value highest top winner max key")
recipe("lookup-table", "dicts", "Lookup table instead of many ifs", '''
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
print(sum(ROMAN[c] for c in "XVI"))

day_names = {1: "Mon", 2: "Tue", 3: "Wed"}
print(day_names.get(2))
''', keys="lookup table mapping dictionary roman numerals replace if elif")
recipe("set-ops", "dicts", "Sets: in both, in either, in one but not the other", '''
a = {1, 2, 3}
b = {2, 3, 4}
print(a & b)
print(a | b)
print(a - b)
print(2 in a)
''', keys="set intersection union difference common shared both", lesson="level-5")
recipe("group", "dicts", "Group items into lists", '''
words = ["apple", "avocado", "banana", "blueberry", "cherry"]
groups = {}
for w in words:
    groups.setdefault(w[0], []).append(w)
print(groups)
''', keys="group by category setdefault defaultdict bucket")
recipe("invert-dict", "dicts", "Swap keys and values", '''
codes = {"a": 1, "b": 2}
print({v: k for k, v in codes.items()})
''', keys="invert swap reverse dictionary keys values comprehension")

# Loops and functions
recipe("range", "loops", "Count with range()", '''
print(list(range(5)))
print(list(range(1, 6)))
print(list(range(10, 0, -2)))
''', keys="range loop count numbers step countdown for", lesson="level-3")
recipe("for-each", "loops", "Loop over a list or string", '''
for fruit in ["apple", "pear"]:
    print(fruit)
for letter in "hi":
    print(letter)
''', keys="for loop each item iterate", lesson="level-3")
recipe("enumerate", "loops", "Loop with the position: enumerate()", '''
for i, name in enumerate(["Ada", "Linus"], start=1):
    print(f"{i}. {name}")
''', keys="enumerate index position counter numbered loop")
recipe("zip", "loops", "Loop over two lists together: zip()", '''
names = ["Ada", "Linus"]
ages = [36, 21]
for name, age in zip(names, ages):
    print(name, age)
print(dict(zip(names, ages)))
''', keys="zip pair two lists together parallel combine")
recipe("while", "loops", "Keep going until something changes: while", '''
n = 100
steps = 0
while n > 1:
    n //= 2
    steps += 1
print(steps)
''', keys="while loop until condition repeat", lesson="level-3")
recipe("break-continue", "loops", "Stop a loop early or skip one: break, continue", '''
for n in range(1, 10):
    if n % 2 == 0:
        continue
    if n > 6:
        break
    print(n)
''', keys="break continue skip stop exit loop early")
recipe("nested-loops", "loops", "A loop inside a loop", '''
for row in range(1, 4):
    print(" ".join(f"{row * col:2}" for col in range(1, 4)))
''', keys="nested loops multiplication table grid")
recipe("function", "loops", "Write a function that returns a value", '''
def area(width, height=1):
    return width * height

print(area(3, 4))
print(area(5))
''', keys="def function return parameter argument default", lesson="level-6",
    note="return hands the value back; print only shows it. A function without return gives None.")
recipe("recursion", "loops", "Recursion: a function that calls itself", '''
def factorial(n):
    if n <= 1:          # base case: stops the calls
        return 1
    return n * factorial(n - 1)

def hanoi_moves(disks):
    return 0 if disks == 0 else 2 * hanoi_moves(disks - 1) + 1

print(factorial(5), hanoi_moves(3))
''', keys="recursion recursive base case factorial hanoi")
recipe("lambda", "loops", "Small one-line functions: lambda", '''
double = lambda x: x * 2
print(double(4))
print(sorted(["b", "A", "c"], key=lambda s: s.lower()))
''', keys="lambda anonymous function key")

# Files, CSV, JSON
recipe("read-file", "files", "Read a whole file", '''
with open("poem.txt", encoding="utf-8") as f:
    text = f.read()
print(len(text.split()), "words")
print(text.splitlines()[0])
''', keys="read file open text contents", files=["poem.txt"], lesson="level-9")
recipe("read-lines", "files", "Read a file line by line", '''
with open("poem.txt", encoding="utf-8") as f:
    for number, line in enumerate(f, start=1):
        line = line.strip()
        if line:
            print(number, line)
''', keys="read lines line by line loop file strip newline", files=["poem.txt"], lesson="level-9")
recipe("skip-bad-lines", "files", "Skip broken lines in a data file", '''
total = count = 0
with open("sensor-data-1k.txt", encoding="utf-8") as f:
    for line in f:
        try:
            value = float(line.split()[2])   # 3rd column: temperature
        except (ValueError, IndexError):
            continue                         # a broken line: ignore it
        total += value
        count += 1
print(count, "good lines")
print(f"average {total / count:.2f}")
''', keys="skip broken bad lines invalid data try except average sensor file", files=["sensor-data-1k.txt"])
recipe("write-file", "files", "Write or add to a file", '''
with open("log.txt", "w", encoding="utf-8") as f:
    f.write("first line\\n")
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("added line\\n")
with open("log.txt", encoding="utf-8") as f:
    print(f.read())
''', keys="write file save append create output w a mode", lesson="level-9",
    note='"w" empties the file the moment it opens; "a" adds to the end.')
recipe("csv-reader", "files", "Read a CSV file", '''
import csv
with open("grades.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)           # skip the header row
    for row in list(reader)[:3]:
        print(row[0], row[2])
print(header)
''', keys="csv read rows columns header skip comma separated", files=["grades.csv"], lesson="level-10")
recipe("csv-dictreader", "files", "Read CSV rows as dictionaries", '''
import csv
with open("grades.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print(rows[0])
marked = [r for r in rows if r["score"].isdigit()]   # skip "absent"
best = max(marked, key=lambda r: int(r["score"]))
print(best["name"], best["score"])
''', keys="csv dictreader dict rows by column name header", files=["grades.csv"], lesson="level-10",
    note="Everything read from a CSV is text. Convert numbers with int() or float() before comparing them.")
recipe("csv-write", "files", "Write a CSV file", '''
import csv
rows = [{"name": "Ada", "score": 82}, {"name": "Linus", "score": 95}]
with open("out.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "score"])
    writer.writeheader()
    writer.writerows(rows)
print(open("out.csv", encoding="utf-8").read())
''', keys="csv write save rows dictwriter writer output", lesson="level-10")
recipe("json", "files", "Save and load JSON", '''
import json
data = {"name": "Ada", "scores": [82, 95]}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
with open("data.json", encoding="utf-8") as f:
    loaded = json.load(f)
print(loaded["scores"])
print(json.dumps(data))
''', keys="json save load dump store data file dictionary", lesson="level-11")
recipe("file-exists", "files", "Check a file exists, handle a missing file", '''
from pathlib import Path
print(Path("poem.txt").exists(), Path("nope.txt").exists())
try:
    open("nope.txt")
except FileNotFoundError:
    print("No such file")
''', keys="file exists missing not found filenotfounderror path check", files=["poem.txt"], lesson="level-9")
recipe("count-file", "files", "Count lines, words and characters in a file", '''
with open("poem.txt", encoding="utf-8") as f:
    text = f.read()
print(len(text.splitlines()), "lines")
print(len(text.split()), "words")
print(len(text), "characters")
''', keys="count lines words characters file statistics wc", files=["poem.txt"])

# Dates and times
recipe("parse-date", "dates", "Text to a date: strptime()", '''
from datetime import datetime
when = datetime.strptime("2026-11-12 14:30", "%Y-%m-%d %H:%M")
print(when)
print(when.year, when.month, when.hour)
''', keys="parse date time string to datetime strptime convert format codes")
recipe("format-date", "dates", "Date to text: strftime()", '''
from datetime import date
d = date(2026, 11, 12)
print(d.strftime("%d/%m/%Y"))
print(d.strftime("%A %d %B %Y"))
print(d.isoformat())
''', keys="format date string strftime day name month name weekday convert",
    note="%Y year, %m month, %d day, %H hour (24h), %M minute, %S second, %A weekday name, %B month name.")
recipe("days-between", "dates", "Days between two dates", '''
from datetime import date
start = date(2026, 11, 12)
final = date(2026, 12, 1)
print((final - start).days)
''', keys="days between dates difference subtract count days until")
recipe("add-days", "dates", "Add days or hours: timedelta", '''
from datetime import datetime, timedelta
start = datetime(2026, 11, 12, 8, 0)
print(start + timedelta(days=7))
print(start + timedelta(hours=30, minutes=15))
''', keys="add days hours minutes timedelta future past date arithmetic")
recipe("time-diff", "dates", "Time between two clock times", '''
from datetime import datetime
fmt = "%H:%M"
gap = datetime.strptime("17:45", fmt) - datetime.strptime("09:10", fmt)
seconds = int(gap.total_seconds())
print(gap)
print(seconds // 3600, "h", seconds % 3600 // 60, "min")
''', keys="time difference duration hours minutes total_seconds clock")
recipe("weekday", "dates", "Day of the week", '''
from datetime import date
d = date(2026, 11, 12)
print(d.weekday())
print(d.strftime("%A"))
print(d.isocalendar().week, "is the week number")
''', keys="weekday day of week monday name week number isocalendar")

# Errors and checking input
recipe("try-except", "errors", "Catch a bad number: try / except ValueError", '''
for text in ["42", "4.5", "abc"]:
    try:
        print(int(text) * 2)
    except ValueError:
        print(f"{text!r} is not a whole number")
''', keys="try except valueerror catch error invalid input number", lesson="level-7")
recipe("ask-again", "errors", "Ask again until the input is valid", '''
answers = iter(["ten", "-3", "7"])   # stands in for input() here
while True:
    text = next(answers)
    try:
        n = int(text)
    except ValueError:
        print("Please type a number")
        continue
    if n > 0:
        break
    print("Must be above 0")
print("Got", n)
''', keys="validate input loop ask again until valid while true break", lesson="level-7")
recipe("zero-division", "errors", "Avoid dividing by zero", '''
def average(nums):
    if not nums:
        return 0
    return sum(nums) / len(nums)

print(average([]))
try:
    print(1 / 0)
except ZeroDivisionError:
    print("can't divide by zero")
''', keys="zerodivisionerror divide by zero empty list average")
recipe("error-message", "errors", "Show the error message", '''
try:
    int("12.5")
except ValueError as error:
    print("Problem:", error)
''', keys="exception message as e print error details")
recipe("raise", "errors", "Raise your own error", '''
def set_age(age):
    if age < 0:
        raise ValueError("age can't be negative")
    return age

try:
    set_age(-1)
except ValueError as error:
    print(error)
''', keys="raise throw error exception custom validation")
recipe("key-index-errors", "errors", "KeyError and IndexError, and how to avoid them", '''
ages = {"Ada": 36}
print(ages.get("Bob", 0))
items = [1, 2]
print(items[5] if len(items) > 5 else "no item 5")
''', keys="keyerror indexerror out of range missing key avoid")

# Printing and formatting
recipe("fstring", "print", "Put values into text: f-strings", '''
name, score = "Ada", 9.5
print(f"{name} scored {score}")
print(f"{name=}")
print(f"{2 + 3 = }")
''', keys="f-string format string interpolation variables in text", lesson="level-1")
recipe("decimals-commas", "print", "Decimals, thousands commas, percent", '''
x = 1234567.891
print(f"{x:.2f}")
print(f"{x:,.2f}")
print(f"{0.4567:.1%}")
''', keys="format decimals 2dp thousands separator comma percent money")
recipe("align", "print", "Line up columns: padding", '''
rows = [("Ada", 82.5), ("Grace", 9)]
for name, score in rows:
    print(f"{name:<8}|{score:>7.1f}|")
print(f"{7:03}")
print("title".center(11, "*"))
''', keys="align columns pad padding width left right center table zfill leading zeros", lesson="level-2")
recipe("print-options", "print", "print() options: sep and end", '''
print("a", "b", "c", sep=", ")
print("no newline", end="")
print(" <- same line")
print(*[1, 2, 3])
''', keys="print sep end newline same line list without brackets separator")
recipe("print-list", "print", "Print a list nicely", '''
items = ["eggs", "milk", "bread"]
print(", ".join(items))
for i, item in enumerate(items, start=1):
    print(f"{i}. {item}")
''', keys="print list without brackets numbered join")

# ---------------------------------------------------------------- lessons


def text_of(fragment):
    fragment = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "part"


HEADING = re.compile(r'<h([234])([^>]*)>(.*?)</h\1>', re.S)


def add_ids(sid, body):
    used = set(re.findall(r'id="([^"]+)"', body))

    def fix(m):
        level, attrs, inner = m.groups()
        if "id=" in attrs or (level == "2" and "part-title" not in attrs):
            return m.group(0)  # already has an id, or it's the band title
        base = f"{sid}-{slug(text_of(re.sub(r'<span class=\"tag\">.*?</span>', '', inner)))}"
        new, n = base, 2
        while new in used:
            new, n = f"{base}-{n}", n + 1
        used.add(new)
        return f'<h{level}{attrs} id="{new}">{inner}</h{level}>'

    return HEADING.sub(fix, body)


def lesson_docs(sid, where, body):
    docs = []
    marks = [m for m in HEADING.finditer(body) if 'id="' in m.group(2)]
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        chunk = body[m.end():end]
        tag = re.search(r'<span class="tag">(.*?)</span>', m.group(3))
        title = text_of(re.sub(r'<span class="tag">.*?</span>', "", m.group(3)))
        code = re.search(r'<code class="language-python">(.*?)</code>', chunk, re.S)
        docs.append({"id": re.search(r'id="([^"]+)"', m.group(2)).group(1), "lesson": sid, "title": title,
                     "where": where + (f" · {tag.group(1)}" if tag else ""),
                     "text": text_of(chunk)[:1200],
                     "code": html.unescape(code.group(1))[:400] if code else ""})
    return docs


# Class names the site already uses for something else.
RENAME = {"hero": "l-hero", "steps": "l-steps", "badge": "l-badge", "plan": "l-plan", "note": "l-note"}


def rename_classes(body):
    return re.sub(r'class="([^"]*)"', lambda m: 'class="' + " ".join(RENAME.get(c, c) for c in m.group(1).split()) + '"', body)


# ---------------------------------------------------------------- how the levels connect
# Each level only uses what it and the levels before it teach. features() says which level teaches each thing
# a piece of code uses; the build fails if a lesson reaches ahead (apart from ORDER_OK), and it decides which
# level each practice problem belongs to from its reference solution.

STR_METHODS = {"upper", "lower", "title", "strip", "lstrip", "rstrip", "replace", "split", "join", "startswith",
               "endswith", "find", "count", "index", "isdigit", "isalpha", "isupper", "islower", "capitalize", "center",
               "ljust", "rjust", "zfill", "splitlines", "swapcase", "isalnum", "isspace"}
LIST_METHODS = {"append", "insert", "extend", "pop", "remove", "sort", "reverse", "copy", "clear"}
DICT_METHODS = {"get", "items", "keys", "values", "add", "update", "setdefault", "discard"}
CALL_LEVEL = {"sorted": 4, "enumerate": 4, "sum": 4, "min": 4, "max": 4, "list": 4, "map": 4, "reversed": 4,
              "zip": 5, "dict": 5, "set": 5, "tuple": 5, "open": 9}
IMPORT_LEVEL = {"pathlib": 9, "csv": 10, "json": 11, "turtle": 13}  # every other import is Level 8

# (lesson level, level of the feature, feature): deliberate early uses, each explained in the lesson itself.
ORDER_OK = {
    (2, 4, "list"),             # ", ".join(["a", "b"]): the list that .split() gives back
    (3, 8, "import"),           # Guess the number needs random; the lesson says Level 8 covers it
    (4, 5, "tuple unpacking"),  # for position, score in enumerate(...)
    (7, 8, "import"), (7, 9, "import"), (7, 10, "import"), (7, 11, "import"),  # the Bug Lab bonus breaks
    (7, 9, "open()"), (7, 9, "with"),                                           # real file code on purpose
}


def features(code):
    """{(level, feature): line} for the Python in code. Snippets that don't parse whole are read line by line."""
    try:
        trees = [ast.parse(code)]
    except SyntaxError:
        trees = []
        for line in code.splitlines():
            try:
                trees.append(ast.parse(line.strip()))
            except SyntaxError:
                pass
    out = {}

    def add(level, what, node):
        out.setdefault((level, what), getattr(node, "lineno", 0))

    for tree in trees:
        for n in ast.walk(tree):
            if isinstance(n, (ast.Subscript, ast.Slice)): add(2, "indexing", n)
            if isinstance(n, ast.Compare) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops): add(2, "in", n)
            if isinstance(n, (ast.If, ast.IfExp)): add(3, "if", n)
            if isinstance(n, (ast.For, ast.While)): add(3, "loop", n)
            if isinstance(n, (ast.List, ast.ListComp)): add(4, "list", n)
            if isinstance(n, (ast.Dict, ast.DictComp)): add(5, "dict", n)
            if isinstance(n, (ast.Set, ast.SetComp)): add(5, "set", n)
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Tuple) for t in n.targets):
                splits = isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "split"
                add(2 if splits else 5, "split into names" if splits else "tuple unpacking", n)  # a, b = line.split() is Level 2
            if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple): add(5, "tuple unpacking", n)
            if isinstance(n, (ast.FunctionDef, ast.Lambda)): add(6, "def/lambda", n)
            if isinstance(n, (ast.Try, ast.Raise)): add(7, "try/raise", n)
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                for mod in mods:
                    add(IMPORT_LEVEL.get(mod.split(".")[0], 8), "import", n)
            if isinstance(n, ast.With): add(9, "with", n)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in CALL_LEVEL:
                add(CALL_LEVEL[n.func.id], n.func.id + "()", n)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                a = n.func.attr
                level = 2 if a in STR_METHODS else 4 if a in LIST_METHODS else 5 if a in DICT_METHODS else 0
                if level:
                    add(level, f".{a}()", n)
    return out


def code_level(code):
    return max([1] + [lv for lv, _ in features(code)])


# What each level builds on: (anchor in an earlier level, what it reuses). "Comes back in" is worked out from this.
USES = {
    2: [("l1-lesson", "Level 1: input() always gives text"), ("level-1-putting-values-into-text", "Level 1: f-strings")],
    3: [("level-1-operators", "Level 1: comparisons, and / or, +="), ("l2-lesson", "Level 2: in and .lower() on text")],
    4: [("level-1-converting-between-types", "Level 1: int() on input"), ("l2-together", "Level 2: .split() and indexes"),
        ("l3-together", "Level 3: counting in a loop"), ("l3-input", "Level 3: loops that read input")],
    5: [("l2-together", "Level 2: cleaning and splitting input"), ("l3-together", "Level 3: the counter pattern"),
        ("l4-lesson", "Level 4: lists and sorting")],
    6: [("l3-input", "Level 3: asking until the input is valid"), ("l4-lesson", "Level 4: lists, sum() and len()"),
        ("l5-together", "Level 5: counting words in a dict")],
    7: [("level-1-converting-between-types", "Level 1: int() on input"), ("l3-input", "Level 3: while loops that ask again"),
        ("l4-mistakes", "Level 4: reaching past the end of a list"), ("level-5-dictionaries", "Level 5: missing dict keys"),
        ("l6-lesson", "Level 6: functions")],
    8: [("l4-lesson", "Level 4: lists, sum() and len()"), ("l5-together", "Level 5: counting with a dict"),
        ("l6-lesson", "Level 6: calling functions with arguments")],
    9: [("l2-lesson", "Level 2: .strip() and .split()"), ("l4-together", "Level 4: building a list in a loop"),
        ("l5-together", "Level 5: counting into a dict"), ("l7-lesson", "Level 7: try / except")],
    10: [("level-1-converting-between-types", "Level 1: int() and float() on text"), ("l5-together", "Level 5: lists of dicts"),
         ("l6-lesson", "Level 6: lambda for key="), ("l9-lesson", "Level 9: opening files with with")],
    11: [("l5-lesson", "Level 5: dicts and lists"), ("l7-lesson", "Level 7: try / except FileNotFoundError"),
         ("level-9-paths-that-work-from-anywhere", "Level 9: Path")],
    12: [("l3-input", "Level 3: input loops and menus"), ("l5-together", "Level 5: totals per category"),
         ("l6-lesson", "Level 6: one job per function"), ("l7-lesson", "Level 7: checking input"),
         ("l10-lesson", "Level 10: CSV"), ("l11-lesson", "Level 11: JSON")],
    13: [("l3-lesson", "Level 3: loops"), ("l4-lesson", "Level 4: lists"), ("l6-lesson", "Level 6: functions with parameters"),
         ("l8-together", "Level 8: random")],
}
# Function finder pages to look things up in while on a level.
CATS = {1: ["convert", "numbers", "print"], 2: ["text", "print"], 3: ["loops"], 4: ["lists"], 5: ["dicts"], 6: ["loops"],
        7: ["errors"], 8: ["numbers", "dates"], 9: ["files"], 10: ["files"], 11: ["files"]}

LEVEL_WORDS = re.compile(r"\bLevels? \d+\b(?:(?:, | and | or | to )\d+\b)*(?! of\b)")  # not the band's "Level 4 of 13"
SKIP_TAGS = {"a", "pre", "code", "button", "h1", "h2", "h3", "h4"}


def linkify(sid, body):
    """Turn "Level 3" / "Levels 9, 10, 11" in lesson text into links (not inside links, code or headings)."""
    own = sid.split("-")[1] if sid.startswith("level-") else ""
    depth, out = 0, []
    for part in re.split(r"(<[^>]+>)", body):
        tag = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
        if tag:
            name = tag.group(2).lower()
            if name in SKIP_TAGS:  # the band's "Level 4 of 13" is left alone by the (?! of) in LEVEL_WORDS
                depth += -1 if tag.group(1) else 1
            out.append(part)
        elif depth or "Level" not in part:
            out.append(part)
        else:
            out.append(LEVEL_WORDS.sub(lambda m: _level_links(m.group(0), own), part))
    return "".join(out)


def _level_links(words, own):
    """"Level 3" links as a whole; "Levels 9, 10, 11" links each number. A level's mention of itself stays text."""
    ok = lambda n: n != own and 1 <= int(n) <= 13
    nums = re.findall(r"\d+", words)
    if len(nums) == 1:
        return f'<a class="lvl-link" href="#level-{nums[0]}">{words}</a>' if ok(nums[0]) else words
    return re.sub(r"\d+", lambda d: f'<a class="lvl-link" href="#level-{d.group(0)}">{d.group(0)}</a>' if ok(d.group(0)) else d.group(0), words)


def check_order(lessons):
    bad = []
    for l in lessons:
        if not l["num"]:
            continue
        level = int(l["num"])
        for c in re.finditer(r'<code class="language-python">(.*?)</code>', l["html"], re.S):
            for (lv, what), line in features(html.unescape(re.sub(r"<[^>]+>", "", c.group(1)))).items():
                if lv > level and (level, lv, what) not in ORDER_OK:
                    bad.append(f"Level {level} uses {what} (taught in Level {lv}): {text_of(c.group(1))[:80]}")
    assert not bad, "lessons reach ahead:\n" + "\n".join(bad)


def _links(items):
    return "".join(f'<li><a href="#{html.escape(a)}">{html.escape(t)}</a></li>' for a, t in items)


def add_panels(l, n, title):
    """A "Builds on" line under the level's chips, and a "Practice and connections" part before its end.
    Solved ticks and the student's own mistakes are filled in by js/learn.js."""
    body = l["html"]
    uses = (f'<p class="builds-on"><span>Builds on</span>{"".join(f"<a href=\"#{a}\">{html.escape(t)}</a>" for a, t in l["uses"])}</p>'
            if l["uses"] else '<p class="builds-on"><span>Starts from zero</span>Every later level builds on this one.</p>')
    chips_end = body.index("</ul>", body.index('<ul class="chips">'))
    chip = f'<li><a href="#l{n}-connect">Practice and connections</a></li>\n  '
    body = body[:chips_end] + chip + "</ul>\n  " + uses + body[chips_end + len("</ul>"):]
    cat = {c["id"]: c["title"] for c in CATEGORIES}
    problem_title = {p["id"]: p["title"] for p in PROBLEMS}
    problems = ("".join(f'<li data-problem="{pid}"><a href="practice.html#{pid}">{html.escape(problem_title[pid])}</a></li>' for pid in l["problems"])
                or '<li class="ll-none">No practice problem needs exactly this level yet. The project above is your practice.</li>')
    cards = [
        ("Practice problems", "Their reference solutions use nothing past this level.", f'<ul class="ll-problems">{problems}</ul>'),
        ("Builds on", "Revise these if this level feels hard.", f'<ul>{_links(l["uses"])}</ul>' if l["uses"] else '<p class="ll-none">Nothing: this is where it starts.</p>'),
        ("Comes back in", "Later levels that use what you learned here.", f'<ul>{_links(l["next"])}</ul>' if l["next"] else '<p class="ll-none">This is where the levels come together.</p>'),
    ]
    if l["cats"]:
        cards.append(("Look it up", "Short, runnable examples in the Function finder.", f'<ul>{_links([(f"cat-{c}", cat[c]) for c in l["cats"]])}</ul>'))
    panel = (f'<h2 class="part-title" id="l{n}-connect"><span class="tag">Next</span>Practice and connections</h2>\n<div class="ll-grid">'
             + "".join(f'<section class="ll-card"><h3>{t}</h3><p class="ll-help">{h}</p>{c}</section>' for t, h, c in cards)
             + f'<section class="ll-card ll-mistakes" data-level="{n}" hidden><h3>Your mistakes on this level</h3>'
               '<p class="ll-help">From your failed runs on the Practice page.</p><ul></ul></section></div>\n')
    end = body.index('<div class="level-end">')
    return body[:end] + panel + body[end:]


def connect(lessons):
    """Adds uses / next / problems / cats to each level and checks every link target exists."""
    where = {}  # anchor id -> level number
    for l in lessons:
        for i in re.findall(r'id="([^"]+)"', l["html"]):
            where.setdefault(i, int(l["num"]) if l["num"] else 0)
        where.setdefault(l["id"], int(l["num"]) if l["num"] else 0)
    title = {int(l["num"]): l["title"] for l in lessons if l["num"]}
    where.update({f"l{n}-connect": n for n in title})  # the panels add_panels() puts in below
    for level, uses in USES.items():
        for anchor, _ in uses:
            assert anchor in where, f"Level {level}: unknown anchor {anchor}"
            assert 0 < where[anchor] < level, f"Level {level} can only build on earlier levels, not {anchor}"
    for kind, (anchor, _) in mistakes.LEARN.items():
        assert anchor in where, f"mistakes.LEARN[{kind!r}]: unknown anchor {anchor}"
    problem_level = {p["id"]: code_level(p["solution"]) for p in PROBLEMS}
    for l in lessons:
        if not l["num"]:
            continue
        n = int(l["num"])
        l["uses"] = [list(u) for u in USES.get(n, [])]
        l["next"] = [[f"level-{m}", f"Level {m}: {title[m]}"] for m in sorted(USES)
                     if m > n and any(where[a] == n for a, _ in USES[m])]
        l["problems"] = [p["id"] for p in PROBLEMS if problem_level[p["id"]] == n]
        l["cats"] = CATS.get(n, [])
        l["html"] = add_panels(l, n, title)
        for target in re.findall(r'href="#([^"]+)"', l["html"]):
            assert target in where or target in ("functions",) or target.startswith("cat-"), f"{l['id']}: link to missing #{target}"
    return problem_level


def build_lessons():
    src = SRC.read_text(encoding="utf-8")
    projects = dict(re.findall(r'data-level-item="(\d+)">.*?<span class="proj">(.*?)</span>', src))
    lessons, docs = [], []
    for cls, sid, body in re.findall(r'<section class="view([^"]*)" id="([^"]+)"[^>]*>(.*?)</section>', src, re.S):
        ink = re.search(r"ink-(\w+)", cls)
        band = re.search(r'<p class="kicker">(.*?)</p>\s*<h2>(.*?)</h2>', body, re.S)
        num = sid.split("-")[1] if sid.startswith("level-") else ""
        title = {"start": "Overview", "reference": "Cheat sheet"}.get(sid) or text_of(band.group(2))
        body = linkify(sid, rename_classes(add_ids(sid, body.strip())))
        lessons.append({"id": sid, "num": num, "title": title, "ink": ink.group(1) if ink else "blue",
                        "project": html.unescape(projects.get(num, "")), "html": body})
        where = f"Level {num} · {title}" if num else title
        docs.append({"id": sid, "lesson": sid, "title": title if num else f"{title} (lessons)", "where": where,
                     "text": text_of(re.search(r'<p class="lead">(.*?)</p>', body, re.S).group(1)) if band else "", "code": ""})
        docs += lesson_docs(sid, where, body)
        if sid == "reference":  # one search entry per "To do this, write this" row
            for todo, write, lvl in re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", body):
                docs.append({"id": "reference", "lesson": sid, "title": text_of(todo), "where": f"Cheat sheet · Level {text_of(lvl)}",
                             "text": text_of(write), "code": text_of(write)})
    return lessons, docs


# ---------------------------------------------------------------- build


def add_reference():
    """One entry per built-in and method (tools/reference.py), after the task-style recipes."""
    import reference
    CATEGORIES.extend(reference.CATEGORIES)
    for cat, entries in reference.R.items():
        for name, what, code, note in entries:
            words = re.sub(r"[^a-z_ ]", " ", name.lower())
            recipe(f"{cat}-{slug(name)}", cat, f"{name}: {what}", code, keys=f"{words} {words.replace('_', ' ')} {what}",
                   note=note, lesson=reference.LESSON.get(cat, ""))


def build():
    add_reference()
    cats = {c["id"] for c in CATEGORIES}
    ids = [r["id"] for r in RECIPES]
    assert len(ids) == len(set(ids)), "duplicate recipe id"
    lessons, docs = build_lessons()
    lesson_ids = {l["id"] for l in lessons}
    assert len(lessons) == 15, f"expected start + 13 levels + cheat sheet, got {len(lessons)}"
    check_order(lessons)
    problem_level = connect(lessons)
    for r in RECIPES:
        assert r["cat"] in cats, r["id"]
        assert not r["lesson"] or r["lesson"] in lesson_ids, r["id"]
        r["output"] = run(r["code"], "", r["files"])  # raises if the code errors
    head = "// Generated by tools/build_learn.py. Edit that file, then run it again.\n"
    (SITE / "js" / "lessons.js").write_text(
        head + f"export const lessons = {json.dumps(lessons, ensure_ascii=False)};\n", encoding="utf-8", newline="\n")
    (SITE / "js" / "learn-index.js").write_text(
        head + f"export const categories = {json.dumps(CATEGORIES, ensure_ascii=False, indent=1)};\n"
        f"export const recipes = {json.dumps(RECIPES, ensure_ascii=False, indent=1)};\n"
        f"export const lessonDocs = {json.dumps(docs, ensure_ascii=False)};\n", encoding="utf-8", newline="\n")
    levels = {int(l["num"]): l["title"] for l in lessons if l["num"]}
    (SITE / "js" / "problem-levels.js").write_text(
        head + "// The level each practice problem needs: the highest level its reference solution uses.\n"
        f"export const problemLevel = {json.dumps(problem_level)};\nexport const levelTitle = {json.dumps(levels)};\n",
        encoding="utf-8", newline="\n")
    print(f"wrote {len(lessons)} lessons, {len(docs)} lesson search entries, {len(RECIPES)} recipes")
    for l in lessons:
        if l["num"]:
            print(f"  Level {l['num']:>2}: {len(l['problems'])} problems, builds on {len(l['uses'])}, comes back in {len(l['next'])}")
    unplaced = [pid for pid, lv in problem_level.items() if lv > 13]
    assert not unplaced, unplaced


if __name__ == "__main__":
    build()
