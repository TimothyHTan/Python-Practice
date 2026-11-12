"""Builds js/problems.js: modules, problems, data files and the 7-day plan.

Every test's expected output is produced by running the problem's reference solution
with real Python, so the tests can't drift from the solutions.

Run after editing:  py site/tools/build_problems.py
"""
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "js" / "problems.js"

# ---------------------------------------------------------------- data files


def sensor_file(seed=7, n=1000, bad_at=(37, 211, 480, 702, 955)):
    """bad_at: broken lines the solution must skip."""
    rng = random.Random(seed)
    lines = []
    for i in range(n):
        day, rest = divmod(i, 200)
        h, m = divmod(rest * 4, 60)  # 200 readings 4 minutes apart: 08:00 to 21:16
        stamp = f"2018-11-{day + 3:02d} {8 + h:02d}:{m:02d}:{rng.randrange(60):02d}"
        temp = 18 + 6 * rng.random() + (3 if 12 <= 8 + h <= 15 else 0)
        hum = 35 + 20 * rng.random()
        light = 120 + 600 * rng.random()
        volt = 2.6 + 0.1 * rng.random()
        if i in bad_at:
            lines.append(f"{stamp} {temp:.2f} {hum:.2f}" if i % 2 else "")
        else:
            lines.append(f"{stamp} {temp:.2f} {hum:.2f} {light:.2f} {volt:.5f}")
    return "\n".join(lines) + "\n"


FIRST = ["Marco", "Lena", "Tariq", "Yuki", "Diego", "Amara", "Jonas", "Priya", "Kofi", "Elena",
         "Mateo", "Sofia", "Ravi", "Hana", "Lucas", "Nadia", "Omar", "Ingrid", "Chen", "Bruno"]
LAST = ["Alvarez", "Brandt", "Okafor", "Tanaka", "Sánchez", "Moreau", "Kowalski", "Haddad",
        "Lindqvist", "Ferreira", "Nakamura", "Rossi", "Mensah", "Petrov", "Duarte", "Quinn"]
SPORTS = ["Soccer", "Basketball", "Tennis", "Auto Racing", "Golf", "Boxing", "Football", "Baseball"]


def sports_csv():
    """Invented athletes in the same shape as the school's 2012-19sport.csv."""
    rng = random.Random(2012)
    people = [f"{f} {l}" for f in FIRST for l in LAST]
    rng.shuffle(people)
    rows = []
    for year in range(2012, 2020):
        pays = sorted(rng.sample(range(220, 1300), 10), reverse=True)  # tenths of a million, all different
        for rank, pay10 in enumerate(pays, 1):
            pay = pay10 / 10
            endorse = 0.3 if rank == 10 and year % 3 == 0 else round(pay * rng.uniform(0.05, 0.6), 1)
            salary = round(pay - endorse, 1)
            endorse_txt = f"${int(endorse * 1000)} K" if endorse < 1 else f"${endorse:g} M"
            rows.append([f"#{rank}", people.pop(), f"${pay:g} M", f"${salary:g} M", endorse_txt,
                         rng.choice(SPORTS), str(year)])
    rng.shuffle(rows)  # file order is not pay order, so you have to sort
    lines = ["Rank,Name,Pay,Salary/Winnings,Endorsements,Sport,Year"] + [",".join(r) for r in rows]
    return "\n".join(lines) + "\n"


INFO = """Welcome to the 2026 Asia-Pacific Coding Week!
Teams from 14 schools meet in Hall B at 9:30 a.m. on Day 1.
\tEach team has 3 members, 1 laptop, and exactly 90 minutes.
Rules: no phones; no internet; no copy-paste from old projects.
Questions? Ask a volunteer (look for the yellow T-shirts).
Good luck, and have fun -- the best team wins a trip to Kyoto!
"""

POEM = """The river does not hurry,
yet it reaches every sea.
It carves the stubborn mountain
one patient grain at a time.

Be like the river, student:
loop, and loop, and loop again,
until the hardest problem
wears smooth beneath your hand.
"""

GRADES = """name,class,score
Ava,7A,88
Ben,7B,72
Cara,7A,91
Dev,7C,65
Eli,7B,absent
Fay,7C,79
Gus,7A,70
Hui,7B,94
Ida,7C,82
Jae,7B,61
"""

# Other versions of the data files, used only by hidden tests (same file name, different content),
# so code that prints a remembered answer instead of reading the file fails.
SENSOR_B = sensor_file(seed=11, n=60, bad_at=(3, 17, 40))
SENSOR_C = sensor_file(seed=99, n=25, bad_at=(0, 24))  # first and last line broken
SENSOR_D = sensor_file(seed=5, n=8, bad_at=(2,))
POEM_B = """Code is a kind of poetry,

and bugs are rhymes that nobody asked for.
Fix one, find two!
"""
POEM_C = """Short.


Lines; with: punctuation -- everywhere
	and tabs	inside
"""
GRADES_B = """name,class,score
Ann,8A,90
Bo,8B,80
Cy,8A,70
Di,8B,80
Ed,8C,absent
Flo,8C,85
"""
GRADES_C = """name,class,score
Kim,9Z,50
Lee,9Z,n/a
Max,9Z,75
"""
GRADES_D = """name,class,score
Ola,6B,60
Pia,6A,60
Quin,6A,
Rui,6B,abc
"""  # two classes tie at 60.00, so the name order decides
POEM_D = """one line, three words, longest wins: equal
"""
INFO_B = """Hello World 2027!
This file is SHORT, but it has: commas, colons; and a tab	here.
Zebras zigzag -- xylophones quiz you.
"""

FILES = {
    "sensor-data-1k.txt": sensor_file(),
    "2012-19sport.csv": sports_csv(),
    "info.txt": INFO,
    "poem.txt": POEM,
    "grades.csv": GRADES,
}

# ---------------------------------------------------------------- modules

# Learn-page pages a module or plan day points to (ids are checked by test/grade.test.mjs).
READ = {
    "level-1": "Level 1: Basics", "level-2": "Level 2: Strings", "level-3": "Level 3: Decisions and loops",
    "level-4": "Level 4: Lists", "level-5": "Level 5: Tuples, dicts and sets", "level-6": "Level 6: Functions",
    "level-7": "Level 7: Errors and debugging", "level-9": "Level 9: Files", "level-10": "Level 10: CSV",
    "reference": "Cheat sheet", "cat-convert": "Functions: converting types", "cat-text": "Functions: strings and letters",
    "cat-numbers": "Functions: numbers and maths", "cat-dates": "Functions: dates and times", "cat-dicts": "Functions: dicts and sets",
    "cat-loops": "Functions: loops", "cat-files": "Functions: files and CSV", "cat-print": "Functions: printing",
}


def read(*ids):
    return [[i, READ[i]] for i in ids]


MODULES = [
    {"id": "basics", "title": "Warm-up basics", "read": read("level-1", "cat-print")},
    {"id": "strings", "title": "Strings, slicing and errors", "read": read("level-2", "level-7", "cat-text")},
    {"id": "numbers", "title": "Numbers and dates", "read": read("level-1", "cat-numbers", "cat-dates")},
    {"id": "collections", "title": "Lists, sets and dictionaries", "read": read("level-4", "level-5", "cat-dicts")},
    {"id": "loops", "title": "Loops and recursion", "read": read("level-3", "level-6", "cat-loops")},
    {"id": "files", "title": "Files and CSV", "read": read("level-9", "level-10", "cat-files")},
    {"id": "text", "title": "Text and ciphers", "read": read("level-2", "level-5", "cat-convert")},
]

# ---------------------------------------------------------------- problems
# Fields: id, module, title, description (list; `code` in backticks), starter, solution,
# tests [(input, sample?)], optional: files, school (pre-final number), tips, note.

P = []


def problem(**kw):
    P.append(kw)


# Warm-up basics (the original eight)
problem(id="vertical-hello", module="basics", title="Hello, vertical world!",
        description=["Print the text `Hello, world!` vertically: one character per line.",
                     "The space between the comma and `w` becomes an empty line."],
        starter='# Print each character of "Hello, world!" on its own line\n',
        solution='for c in "Hello, world!":\n    print(c)\n',
        tests=[("", True)])
problem(id="add-two", module="basics", title="Add two numbers",
        description=["You get one line with two whole numbers separated by a space.", "Print their sum."],
        starter="a, b = input().split()\n",
        solution="a, b = input().split()\nprint(int(a) + int(b))\n",
        tests=[("3 5", True), ("-4 10", True), ("0 0", False), ("123456 654321", False)])
problem(id="even-odd", module="basics", title="Even or odd",
        description=["Read one whole number `n`.", "Print `even` if it is even, otherwise print `odd`."],
        starter="n = int(input())\n",
        solution='n = int(input())\nprint("even" if n % 2 == 0 else "odd")\n',
        tests=[("4", True), ("7", True), ("0", False), ("-3", False)])
problem(id="countdown", module="basics", title="Countdown",
        description=["Read a whole number `n` (1 or more).",
                     "Print the numbers from `n` down to `1`, one per line, then print `Liftoff!`."],
        starter="n = int(input())\n",
        solution='n = int(input())\nfor i in range(n, 0, -1):\n    print(i)\nprint("Liftoff!")\n',
        tests=[("3", True), ("1", True), ("6", False), ("10", False)])
problem(id="reverse-word", module="basics", title="Reverse a word",
        description=["Read one line of text and print it backwards."],
        starter="text = input()\n",
        solution="print(input()[::-1])\n",
        tests=[("python", True), ("racecar", True), ("Hello, world!", False), ("a", False)])
problem(id="count-vowels", module="basics", title="Count the vowels",
        description=["Read one line of text. Print how many vowels it has.",
                     "Vowels are `a e i o u`, upper or lower case."],
        starter="text = input()\n",
        solution='text = input()\nprint(sum(1 for c in text if c in "aeiouAEIOU"))\n',
        tests=[("Hello, world!", True), ("AEIOU aeiou", True), ("rhythm", False), ("Programming Is Fun", False)])
problem(id="fizzbuzz", module="basics", title="FizzBuzz",
        description=["Read a whole number `n`. For every number from `1` to `n`, print one line:",
                     "`FizzBuzz` if it divides by 3 and 5, `Fizz` if it divides by 3, `Buzz` if it divides by 5, otherwise the number itself."],
        starter="n = int(input())\n",
        solution=('n = int(input())\nfor i in range(1, n + 1):\n    if i % 15 == 0:\n        print("FizzBuzz")\n'
                  '    elif i % 3 == 0:\n        print("Fizz")\n    elif i % 5 == 0:\n        print("Buzz")\n'
                  '    else:\n        print(i)\n'),
        tests=[("5", True), ("15", True), ("1", False), ("30", False)])
problem(id="largest", module="basics", title="Largest number",
        description=["The first line is how many numbers there are. The second line has the numbers, separated by spaces.",
                     "Print the largest one."],
        starter="count = int(input())\nnumbers = input().split()\n",
        solution="input()\nprint(max(int(x) for x in input().split()))\n",
        tests=[("4\n3 9 2 7", True), ("3\n-5 -2 -9", True), ("1\n42", False), ("5\n10 100 99 100 3", False)])

# ---- Pre-final problems (from python_practice_notes.md)

problem(id="pf-units", module="strings", school=1, title="Unit conversion: meters and feet",
        description=["The input is a length like `123m` or `99.9876543ft`. Convert it using 1 m = 3.2808 ft.",
                     "Print the result with 2 decimals followed by the new unit (`m` becomes `ft`, `ft` becomes `m`).",
                     "Numbers can be written in hex, binary or octal (`0x1f`, `0b101`, `0o17`). If the input is not a valid length, print `format error`."],
        starter="x = input().strip()\n",
        tips=["Typos like `oor` for `or`, or `==` where you meant `=`.",
              "The factor is 3.2808, not 3.808.",
              "`-0ft` must print `0.00m`: `float(\"-0\")` is negative zero, but `int(\"-0\", 0)` is `0`.",
              "`float()` can't read `0x...`. Try `int(num, 0)` first, then fall back to `float(num)`.",
              "Use `except ValueError:`, never a bare `except:`."],
        solution='''x = input().strip()

if x.endswith("ft"):
    num, unit = x[:-2], "ft"
elif x.endswith("m"):
    num, unit = x[:-1], "m"
else:
    num, unit = "", ""

try:
    try:
        value = int(num, 0)
    except ValueError:
        value = float(num)

    if unit == "m":
        print(f"{value * 3.2808:.2f}ft")
    else:
        print(f"{value / 3.2808:.2f}m")
except ValueError:
    print("format error")
''',
        tests=[("123m", True), ("99.9876543ft", True), ("-0ft", False), ("-0xabcdm", False), ("12", False),
               ("abcm", False), ("0b101m", False), ("1e3ft", False), ("2.5 m", False)])

problem(id="pf-time", module="numbers", school=2, title="Time difference in minutes",
        description=["The input is two date-times separated by a comma, like `2019-12-19 17:18:20,2019-12-20 19:18:20`.",
                     "Print the difference between them in whole minutes. The second time can be earlier than the first."],
        starter="from datetime import datetime\n\n",
        tips=["The hour code is `%H`. `%G` is the ISO year and crashes `strptime`.",
              "`.seconds` ignores whole days. Use `.total_seconds()`.",
              "Use `abs()` because the times can come in either order."],
        solution='''from datetime import datetime

a, b = input().split(",")
fmt = "%Y-%m-%d %H:%M:%S"

t1 = datetime.strptime(a.strip(), fmt)
t2 = datetime.strptime(b.strip(), fmt)

seconds = abs((t2 - t1).total_seconds())
print(int(seconds // 60))
''',
        tests=[("2019-12-19 17:18:20,2019-12-20 19:18:20", True), ("2019-12-20 19:18:20,2019-12-19 17:18:20", False),
               ("2020-02-28 00:00:00,2020-03-01 00:00:00", False), ("2021-06-01 10:00:00,2021-06-01 10:00:59", False),
               ("2018-01-01 00:00:00,2019-01-01 00:00:00", False)])

problem(id="pf-currency", module="strings", school=3, title="Currency conversion: RMB, CNY, Euro, EUR",
        description=["The input is an amount like `123RMB` or `999EUR`. The rate is 1 euro = 7.8942 RMB. Print the converted amount with 2 decimals.",
                     "Keep the naming style of the input: names map to names (`RMB` to `Euro`, `Euro` to `RMB`) and symbols map to symbols (`CNY` to `EUR`, `EUR` to `CNY`).",
                     "Numbers can be hex, binary or octal like problem 1. Anything else prints `format error`."],
        starter="money = input().strip()\n",
        tips=["Don't hardcode the output currency: `Euro` must become `RMB`, `EUR` must become `CNY`.",
              "Handle all four: `RMB`, `CNY`, `Euro`, `EUR`.",
              "Count slice lengths: `\"EUR\"` is 3 letters (`[:-3]`), `\"Euro\"` is 4 (`[:-4]`).",
              "No bare `except:`."],
        solution='''money = input().strip()

if money.endswith("RMB"):
    num, cur, out = money[:-3], "cn", "Euro"
elif money.endswith("CNY"):
    num, cur, out = money[:-3], "cn", "EUR"
elif money.endswith("Euro"):
    num, cur, out = money[:-4], "eu", "RMB"
elif money.endswith("EUR"):
    num, cur, out = money[:-3], "eu", "CNY"
else:
    num, cur, out = "", "", ""

try:
    try:
        value = int(num, 0)
    except ValueError:
        value = float(num)

    if cur == "eu":
        print(f"{value * 7.8942:.2f}{out}")
    else:
        print(f"{value / 7.8942:.2f}{out}")
except ValueError:
    print("format error")
''',
        tests=[("123RMB", True), ("999EUR", True), ("100Euro", False), ("50CNY", False), ("12USD", False),
               ("abcEUR", False), ("0x10RMB", False), ("-2.5Euro", False), ("EUR", False)])

problem(id="pf-permille", module="numbers", school=4, title="Per mille growth",
        description=["The input is `N`, a per mille value (so the daily rate is N/1000).",
                     "Working hard multiplies your ability by `(1 + N/1000)` every day; slacking multiplies it by `(1 - N/1000)`. After 365 days print `up, down, ratio`: the two powers with 2 decimals and the ratio as a whole number."],
        starter="n = float(input())\n",
        note="Your notes say a hidden test on the real platform failed and the cause was never found. The tests here use `int(up / down)` for the ratio, like the reference solution; the real platform may have rounded instead.",
        tips=["A missing `=` (`up ( 1 + ...`) is a `NameError`.",
              "If a hidden test fails, try in order: `round(up / down)`, then the ratio of the rounded powers, then a different format for the ratio."],
        solution='''n = float(input())

up = (1 + n / 1000) ** 365
down = (1 - n / 1000) ** 365

print(f"{up:.2f}, {down:.2f}, {int(up / down)}")
''',
        tests=[("1", True), ("5", True), ("0", False), ("10", False), ("2", False)])

problem(id="pf-unique", module="collections", school=5, title="Count different values in a list",
        description=["The input is a Python list, like `[0, 1, 2, 3, 4, 4.0, 4.00, 3, 2, 1, 0]`.",
                     "Print how many different values it has (`5` here). In Python `4`, `4.0` and `4.00` are equal."],
        starter="lst = eval(input())\n",
        tips=["`eval(input())` turns the typed text into a real list.",
              "Equal values collapse: `4 == 4.0`, and even `True == 1`.",
              "Short version: `len(set(...))`. Practice the loop version too."],
        solution='''lst = eval(input())

unique = []
for item in lst:
    if item not in unique:
        unique.append(item)

count = len(unique)
print(count)
''',
        tests=[("[0, 1, 2, 3, 4, 4.0, 4.00, 3, 2, 1, 0]", True), ("[7, 7, 7]", False), ("[]", False),
               ("[1, True, 1.0, 2]", False), ("['a', 'A', 'a', 'b']", False)])

problem(id="pf-sensor", module="files", school=6, title="Average of the light sensor",
        description=["Read the file `sensor-data-1k.txt`. Each good line has 6 pieces: date, time, temperature, humidity, light, voltage.",
                     "Print the average light value with 2 decimals. Some lines are broken (fewer pieces, or empty): skip them."],
        files=["sensor-data-1k.txt"],
        starter='f = open("sensor-data-1k.txt", "r")\n',
        tips=["Light is the 5th piece, so index `4`.",
              "Skip lines where `len(parts) != 6`, or one broken line crashes everything.",
              "Divide by the number of good lines, not by 1000."],
        solution='''f = open("sensor-data-1k.txt", "r")

total = 0
count = 0

for line in f:
    parts = line.split()
    if len(parts) == 6:
        total = total + float(parts[4])
        count = count + 1

f.close()

print(f"{total / count:.2f}")
''',
        tests=[("", True), ("", False, {"sensor-data-1k.txt": SENSOR_B}), ("", False, {"sensor-data-1k.txt": SENSOR_C}),
               ("", False, {"sensor-data-1k.txt": SENSOR_D})])

problem(id="pf-factors", module="loops", school=7, title="Prime factor decomposition",
        description=["The input is a positive whole number `n`. Print a list of its prime factors, smallest first.",
                     "For example `12` gives `[2, 2, 3]`. For `1` print `[]`."],
        starter="n = int(input())\n",
        tips=["Start the divisor at 2. Divide while it fits, then move on.",
              "Use `//` so `n` stays a whole number.",
              "No prime check needed: smaller primes were already divided out."],
        solution='''n = int(input())

factors = []
d = 2

while n > 1:
    while n % d == 0:
        factors.append(d)
        n = n // d
    d = d + 1

print(factors)
''',
        tests=[("12", True), ("1", False), ("97", False), ("360", False), ("1024", False), ("9973", False)])

problem(id="pf-roman", module="collections", school=8, title="Roman numerals to an integer",
        description=["The input is a legal Roman numeral from 1 to 3999. Print its value.",
                     "For example `MCMIV` gives `1904`."],
        starter="s = input().strip()\n",
        tips=["A dictionary of the 7 letters.",
              "If a letter is smaller than the next one, subtract it, otherwise add it. That covers IV, IX, XL, XC, CD and CM.",
              "Check `i + 1 < len(s)` so the last letter doesn't look past the end."],
        solution='''s = input().strip()

values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

total = 0
for i in range(len(s)):
    if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
        total = total - values[s[i]]
    else:
        total = total + values[s[i]]

print(total)
''',
        tests=[("MCMIV", True), ("III", False), ("IV", False), ("XLII", False), ("MMMCMXCIX", False), ("CDXLIV", False)])

problem(id="pf-hanoi", module="loops", school=9, title="Tower of Hanoi",
        description=["Write a recursive function `move(n, a, b, c)` that moves `n` disks from peg `a` to peg `c`, using `b` as the spare.",
                     "The input is `n` on the first line and the three peg names on the second, like `A B C`. Print each move as `A --> C`."],
        starter="def move(n, a, b, c):\n    pass\n\n\nn = int(input())\na, b, c = input().split()\nmove(n, a, b, c)\n",
        tips=["Base case: `n == 0` does nothing.",
              "Move `n-1` from `a` to `b`, print `a --> c`, move `n-1` from `b` to `c`.",
              "The task text said `->` but the example box used `-->`. These tests use `-->`."],
        solution='''def move(n, a, b, c):
    if n == 0:
        return
    move(n - 1, a, c, b)
    print(a, "-->", c)
    move(n - 1, b, a, c)

n = int(input())
a, b, c = input().split()
move(n, a, b, c)
''',
        tests=[("3\nA B C", True), ("1\nA B C", False), ("2\nX Y Z", False), ("4\nA B C", False)])

problem(id="pf-palprimes", module="loops", school=10, title="Palindromic primes",
        description=["The input is `n`. Print the first `n` primes that read the same backwards, separated by spaces.",
                     "For `10` the output is `2 3 5 7 11 101 131 151 181 191`."],
        starter="n = int(input())\n",
        tips=["Write a helper `is_prime` that only tests divisors up to the square root.",
              "Palindrome check: `s == s[::-1]`.",
              "The task text showed commas but the example uses spaces. Follow the example."],
        solution='''def is_prime(x):
    if x < 2:
        return False
    for i in range(2, int(x ** 0.5) + 1):
        if x % i == 0:
            return False
    return True

def is_palindrome(x):
    s = str(x)
    return s == s[::-1]

n = int(input())

result = []
num = 2
while len(result) < n:
    if is_palindrome(num) and is_prime(num):
        result.append(str(num))
    num = num + 1

print(" ".join(result))
''',
        tests=[("10", True), ("1", False), ("4", False), ("20", False)])

problem(id="pf-sports", module="files", school=11, title="Sports income ranking (CSV)",
        description=["Read `2012-19sport.csv`. Its columns are Rank, Name, Pay, Salary/Winnings, Endorsements, Sport, Year. Money looks like `$93.4 M` (or `$150 K`). The rows are not in pay order.",
                     "If the first input is a year from 2012 to 2019, the second input is `k`. Print the top `k` athletes of that year by pay, one per line, every column separated by ` | `, with the `#` removed from the rank. If `k` is bigger than the number of athletes, print them all.",
                     "If the first input is `sport` (any case), the second input is a year and the third is a sport number. Print that year's sports in alphabetical order as `1: Auto Racing`, then that sport's athletes, then `TOTAL: $607.00 M` (the sum of their pay).",
                     "Anything else prints `Wrong Input`."],
        files=["2012-19sport.csv"],
        starter='import csv\n\nfirst = input().strip()\n',
        note="The athletes in this file are made up. It has the same shape as the school's file, so the same code works on both.",
        tips=["Skip the header row.", "Strip the `#` from the rank.",
              "Convert money to a number before sorting: as text, `$127 M` sorts below `$94 M`.",
              "`[:k]` already handles a `k` that is too big.", "Sport numbers start at 1. Use `sorted(set(...))`.",
              "`Wrong Input` covers years outside 2012 to 2019 and any other text.",
              "If the real file crashes or names look garbled, try `encoding=\"gbk\"`."],
        solution='''import csv

first = input().strip()

rows = []
f = open("2012-19sport.csv", "r", encoding="utf-8")
reader = csv.reader(f)
next(reader)
for r in reader:
    if len(r) >= 7:
        rows.append(r)
f.close()

def show(r):
    rank = r[0].replace("#", "")
    print(rank, "|", r[1], "|", r[2], "|", r[3], "|", r[4], "|", r[5], "|", r[6])

def money(text):
    text = text.replace("$", "").strip()
    if text.endswith("K"):
        return float(text[:-1]) / 1000
    return float(text.replace("M", "").strip())

if first.isdigit() and 2012 <= int(first) <= 2019:
    year = first
    k = int(input())
    year_rows = [r for r in rows if r[6].strip() == year]
    year_rows.sort(key=lambda r: money(r[2]), reverse=True)
    for r in year_rows[:k]:
        show(r)

elif first.lower() == "sport":
    year = input().strip()
    index = int(input())
    year_rows = [r for r in rows if r[6].strip() == year]

    sports = sorted(set(r[5] for r in year_rows))
    for i in range(len(sports)):
        print(f"{i + 1}: {sports[i]}")

    chosen = sports[index - 1]
    total = 0
    for r in year_rows:
        if r[5] == chosen:
            show(r)
            total = total + money(r[2])
    print(f"TOTAL: ${total:.2f} M")

else:
    print("Wrong Input")
''',
        tests=[("2015\n3", True), ("sport\n2018\n1", True), ("2019\n100", False), ("SPORT\n2012\n2", False),
               ("2011\n3", False), ("hello", False), ("2013\n1", False)])

problem(id="pf-caesar", module="text", school=12, title="Text analysis and Caesar encryption",
        description=["Read `info.txt` with the given `read_file` function. The input is a secret word (a weekday). Print, in order:",
                     "1. The number of uppercase letters, lowercase letters, digits, whitespace characters and other characters, separated by spaces.",
                     "2. `A total of N words.` Replace every punctuation character with a space, then `split()` and count.",
                     "3. The shift: the sum of the ASCII values of the secret word, modulo 26 (`Tuesday` gives 735 % 26 = 7).",
                     "4. The file's text encrypted with the Caesar cipher using that shift. Keep upper and lower case, wrap around (`z` to `a`), and copy everything else unchanged."],
        files=["info.txt"],
        starter="import string\n\ndef read_file(file):\n    with open(file, 'r', encoding='utf-8') as f:\n        return f.read()\n\ntext = read_file(\"info.txt\")\nword = input().strip()\n",
        tips=["Whitespace includes `\\n` and `\\t`: use `isspace()`.",
              "Hyphens are punctuation, so `Asia-Pacific` counts as 2 words.",
              "Wrap with `% 26`. Keep the case. Non-letters stay the same.",
              "The school example printed the stats block twice; the second one matched the real file."],
        solution='''import string

def read_file(file):
    with open(file, 'r', encoding='utf-8') as f:
        return f.read()

text = read_file("info.txt")
word = input().strip()

upper = 0
lower = 0
digit = 0
space = 0
other = 0

for c in text:
    if c in string.ascii_uppercase:
        upper = upper + 1
    elif c in string.ascii_lowercase:
        lower = lower + 1
    elif c.isdigit():
        digit = digit + 1
    elif c.isspace():
        space = space + 1
    else:
        other = other + 1

print(upper, lower, digit, space, other)

clean = text
for p in string.punctuation:
    clean = clean.replace(p, " ")
print(f"A total of {len(clean.split())} words.")

shift = 0
for c in word:
    shift = shift + ord(c)
shift = shift % 26
print(shift)

result = ""
for c in text:
    if c in string.ascii_uppercase:
        result = result + chr((ord(c) - ord("A") + shift) % 26 + ord("A"))
    elif c in string.ascii_lowercase:
        result = result + chr((ord(c) - ord("a") + shift) % 26 + ord("a"))
    else:
        result = result + c

print(result)
''',
        tests=[("Tuesday", True), ("Monday", False), ("Friday", False), ("Sunday", False),
               ("Wednesday", False, {"info.txt": INFO_B}), ("Saturday", False, {"info.txt": INFO_B})])

# ---- Drills: short problems that train one idea each

problem(id="kg-lb", module="strings", title="Weight conversion: kg and lb",
        description=["The input is a weight like `10kg` or `22.046lb`. 1 kg = 2.2046 lb.",
                     "Print the converted weight with 2 decimals and the other unit. If the input is not a valid weight, print `format error`."],
        starter="x = input().strip()\n",
        solution='''x = input().strip()

if x.endswith("kg"):
    num, unit = x[:-2], "kg"
elif x.endswith("lb"):
    num, unit = x[:-2], "lb"
else:
    num, unit = "", ""

try:
    value = float(num)
    if unit == "kg":
        print(f"{value * 2.2046:.2f}lb")
    else:
        print(f"{value / 2.2046:.2f}kg")
except ValueError:
    print("format error")
''',
        tests=[("10kg", True), ("22.046lb", True), ("0.5kg", False), ("7", False), ("kg", False), ("-3kg", False), ("abclb", False)])

problem(id="file-extension", module="strings", title="File extension",
        description=["The input is a file name. Print its extension in lower case, without the dot.",
                     "Print `no extension` if there is no dot, if the only dot is the first character (like `.bashrc`), or if the name ends with a dot."],
        starter="name = input().strip()\n",
        solution='''name = input().strip()
i = name.rfind(".")
if i <= 0 or i == len(name) - 1:
    print("no extension")
else:
    print(name[i + 1:].lower())
''',
        tests=[("report.PDF", True), ("archive.tar.gz", True), ("README", False), (".bashrc", False), ("photo.", False)])

problem(id="safe-divide", module="strings", title="Safe division",
        description=["Read two numbers, one per line. Print the first divided by the second with 2 decimals.",
                     "If either line is not a number print `format error`. If the second number is 0 print `division by zero`."],
        starter="a = input().strip()\nb = input().strip()\n",
        solution='''a = input().strip()
b = input().strip()
try:
    x = float(a)
    y = float(b)
    print(f"{x / y:.2f}")
except ValueError:
    print("format error")
except ZeroDivisionError:
    print("division by zero")
''',
        tests=[("7\n2", True), ("1\n0", True), ("ten\n2", False), ("-9\n4", False), ("1e2\n3", False)])

problem(id="any-base", module="strings", title="Read a number in any base",
        description=["The input is a whole number written in Python style: decimal (`42`), hex (`0x1f`), binary (`0b101`) or octal (`0o17`), maybe with a minus sign.",
                     "Print its value in decimal. Anything else, including `3.5` and numbers with leading zeros like `007`, prints `format error`."],
        starter="x = input().strip()\n",
        solution='''x = input().strip()
try:
    print(int(x, 0))
except ValueError:
    print("format error")
''',
        tests=[("0x1f", True), ("0b101", True), ("-0o17", False), ("42", False), ("0x", False), ("3.5", False), ("007", False)])

problem(id="compound-interest", module="numbers", title="Compound interest",
        description=["The input is one line: a starting amount, a yearly interest rate in percent, and a number of years.",
                     "Print the final amount and how many times bigger it got, both with 2 decimals, like `1628.89, 1.63`."],
        starter="p, rate, years = input().split()\n",
        solution='''p, rate, years = input().split()
p = float(p)
amount = p * (1 + float(rate) / 100) ** int(years)
print(f"{amount:.2f}, {amount / p:.2f}")
''',
        tests=[("1000 5 10", True), ("500 0 3", False), ("2000 3.5 20", False), ("100 -10 2", False)])

problem(id="days-between", module="numbers", title="Days between two dates",
        description=["The input is two dates separated by a comma, like `2024-02-28,2024-03-01`.",
                     "Print how many days apart they are. The second date can be earlier."],
        starter="from datetime import datetime\n\n",
        solution='''from datetime import datetime

a, b = input().split(",")
d1 = datetime.strptime(a.strip(), "%Y-%m-%d")
d2 = datetime.strptime(b.strip(), "%Y-%m-%d")
print(abs((d2 - d1).days))
''',
        tests=[("2024-02-28,2024-03-01", True), ("2023-02-28,2023-03-01", False), ("2026-11-18,2026-11-12", False),
               ("2025-12-31,2026-01-01", False)])

problem(id="weekday", module="numbers", title="Day of the week",
        description=["The input is a date like `2026-11-12`. Print its weekday name in English, like `Thursday`."],
        starter="from datetime import datetime\n\n",
        solution='''from datetime import datetime

d = datetime.strptime(input().strip(), "%Y-%m-%d")
print(d.strftime("%A"))
''',
        tests=[("2026-11-12", True), ("2026-11-18", True), ("2000-01-01", False), ("2024-02-29", False), ("1999-12-31", False)])

problem(id="unique-words", module="collections", title="Unique words",
        description=["Read one line of text. Print how many different words it has.",
                     "Ignore upper and lower case, and treat punctuation as spaces."],
        starter="import string\n\ntext = input()\n",
        solution='''import string

text = input().lower()
for p in string.punctuation:
    text = text.replace(p, " ")
print(len(set(text.split())))
''',
        tests=[("The cat and the hat.", True), ("Go, go, GO!", False), ("one-two three", False), ("a b c a b c d", False)])

problem(id="second-largest", module="collections", title="Second largest value",
        description=["The input is a Python list of numbers. Print the second largest different value, or `none` if there isn't one."],
        starter="lst = eval(input())\n",
        solution='''lst = eval(input())
values = sorted(set(lst), reverse=True)
if len(values) < 2:
    print("none")
else:
    print(values[1])
''',
        tests=[("[3, 1, 4, 4, 2]", True), ("[5, 5]", False), ("[1, 2.0, 2]", False), ("[-1, -7, -3]", False)])

problem(id="letter-frequency", module="collections", title="Most common letter",
        description=["Read one line of text. Count letters only, ignoring case.",
                     "Print the most common letter and its count, like `l 3`. If two letters tie, print the one that comes first in the alphabet. If there are no letters, print `no letters`."],
        starter="text = input()\ncounts = {}\n",
        solution='''text = input().lower()
counts = {}
for c in text:
    if c.isalpha():
        counts[c] = counts.get(c, 0) + 1

if not counts:
    print("no letters")
else:
    best = sorted(counts, key=lambda c: (-counts[c], c))[0]
    print(best, counts[best])
''',
        tests=[("Hello, world!", True), ("abcabc", False), ("123 !?", False), ("Mississippi", False)])

problem(id="int-to-roman", module="collections", title="Integer to Roman numerals",
        description=["The reverse of pre-final problem 8. The input is a whole number from 1 to 3999. Print it as a Roman numeral, for example `1904` gives `MCMIV`."],
        starter="n = int(input())\n",
        solution='''n = int(input())
pairs = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
result = ""
for value, letters in pairs:
    while n >= value:
        result = result + letters
        n = n - value
print(result)
''',
        tests=[("1904", True), ("4", False), ("3999", False), ("444", False), ("58", False)])

problem(id="is-prime", module="loops", title="Is it prime?",
        description=["Read a whole number. Print `prime` or `not prime`.",
                     "Only test divisors up to the square root, or the big test will be too slow."],
        starter="n = int(input())\n",
        solution='''n = int(input())

def is_prime(x):
    if x < 2:
        return False
    for i in range(2, int(x ** 0.5) + 1):
        if x % i == 0:
            return False
    return True

print("prime" if is_prime(n) else "not prime")
''',
        tests=[("97", True), ("1", False), ("2", False), ("91", False), ("1000000007", False)])

problem(id="digital-root", module="loops", title="Digital root steps",
        description=["Read a whole number. Keep adding up its digits until one digit is left.",
                     "Print every step joined by ` -> `, like `9875 -> 29 -> 11 -> 2`. A number that already has one digit prints just itself."],
        starter="n = input().strip()\n",
        solution='''n = input().strip()
steps = [n]
while len(n) > 1:
    n = str(sum(int(d) for d in n))
    steps.append(n)
print(" -> ".join(steps))
''',
        tests=[("9875", True), ("7", False), ("99", False), ("123456789", False)])

problem(id="hanoi-count", module="loops", title="Count the Hanoi moves",
        description=["Write a recursive function `count(n)` that returns how many moves it takes to solve the Tower of Hanoi with `n` disks: 0 for no disks, otherwise twice the moves for `n-1` disks plus one.",
                     "Read `n` and print `count(n)`."],
        starter="def count(n):\n    pass\n\n\nprint(count(int(input())))\n",
        solution='''def count(n):
    if n == 0:
        return 0
    return 2 * count(n - 1) + 1

print(count(int(input())))
''',
        tests=[("3", True), ("1", False), ("10", False), ("20", False)])

problem(id="factorial-recursive", module="loops", title="Factorial with recursion",
        description=["Write a recursive function `fact(n)`. `fact(0)` is 1, and `fact(n)` is `n * fact(n - 1)`.",
                     "Read `n` and print `fact(n)`."],
        starter="def fact(n):\n    pass\n\n\nprint(fact(int(input())))\n",
        solution='''def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)

print(fact(int(input())))
''',
        tests=[("5", True), ("0", False), ("1", False), ("20", False)])

problem(id="max-temperature", module="files", title="Hottest and coldest reading",
        description=["Read `sensor-data-1k.txt` (the same file as pre-final problem 6). Skip broken lines.",
                     "Print `Max 27.43 at 2018-11-03 14:02:11` for the hottest reading and `Min ...` in the same style for the coldest. If two readings tie, keep the first one."],
        files=["sensor-data-1k.txt"],
        starter='f = open("sensor-data-1k.txt", "r")\n',
        solution='''f = open("sensor-data-1k.txt", "r")
best = None
worst = None
for line in f:
    parts = line.split()
    if len(parts) != 6:
        continue
    t = float(parts[2])
    if best is None or t > best[0]:
        best = (t, parts[0], parts[1])
    if worst is None or t < worst[0]:
        worst = (t, parts[0], parts[1])
f.close()
print(f"Max {best[0]:.2f} at {best[1]} {best[2]}")
print(f"Min {worst[0]:.2f} at {worst[1]} {worst[2]}")
''',
        tests=[("", True), ("", True, {"sensor-data-1k.txt": SENSOR_D}), ("", False, {"sensor-data-1k.txt": SENSOR_B}),
               ("", False, {"sensor-data-1k.txt": SENSOR_C})])

problem(id="poem-stats", module="files", title="Poem statistics",
        description=["Read `poem.txt`. Print three lines: `Lines: N` (count non-empty lines only), `Words: N`, and `Longest word: x`.",
                     "Treat punctuation as spaces. If several words are equally long, print the first one."],
        files=["poem.txt"],
        starter='import string\n\ntext = open("poem.txt", "r").read()\n',
        solution='''import string

text = open("poem.txt", "r").read()
lines = [l for l in text.split("\\n") if l.strip()]
clean = text
for p in string.punctuation:
    clean = clean.replace(p, " ")
words = clean.split()
longest = ""
for w in words:
    if len(w) > len(longest):
        longest = w
print(f"Lines: {len(lines)}")
print(f"Words: {len(words)}")
print(f"Longest word: {longest}")
''',
        tests=[("", True), ("", True, {"poem.txt": POEM_B}), ("", False, {"poem.txt": POEM_C}), ("", False, {"poem.txt": POEM_D})])

problem(id="class-averages", module="files", title="Class averages (CSV)",
        description=["Read `grades.csv` (columns name, class, score). Skip rows where the score is not a number.",
                     "Print each class and its average score with 2 decimals, like `7A: 83.00`, highest average first. If two classes tie, sort them by name."],
        files=["grades.csv"],
        starter='import csv\n\nf = open("grades.csv", "r")\n',
        solution='''import csv

f = open("grades.csv", "r")
reader = csv.reader(f)
next(reader)
totals = {}
counts = {}
for name, cls, score in reader:
    try:
        s = float(score)
    except ValueError:
        continue
    totals[cls] = totals.get(cls, 0) + s
    counts[cls] = counts.get(cls, 0) + 1
f.close()

averages = [(cls, totals[cls] / counts[cls]) for cls in totals]
averages.sort(key=lambda pair: (-pair[1], pair[0]))
for cls, avg in averages:
    print(f"{cls}: {avg:.2f}")
''',
        tests=[("", True), ("", True, {"grades.csv": GRADES_C}), ("", False, {"grades.csv": GRADES_B}), ("", False, {"grades.csv": GRADES_D})])

problem(id="caesar-decrypt", module="text", title="Caesar decryption",
        description=["The first line is a shift (it can be bigger than 26 or negative). The second line is text that was encrypted with that shift.",
                     "Print the original text: shift letters back, keep the case, leave everything else unchanged."],
        starter="shift = int(input())\ntext = input()\n",
        solution='''shift = int(input())
text = input()
result = ""
for c in text:
    if c.isupper() and c.isascii():
        result = result + chr((ord(c) - ord("A") - shift) % 26 + ord("A"))
    elif c.islower() and c.isascii():
        result = result + chr((ord(c) - ord("a") - shift) % 26 + ord("a"))
    else:
        result = result + c
print(result)
''',
        tests=[("3\nKhoor, Zruog!", True), ("7\nAol mpuhs pz uvd!", False), ("29\nKhoor", False), ("-1\nzab", False)])

# ---------------------------------------------------------------- difficulty: 1 easy, 2 medium, 3 hard
# Problems are listed easiest first inside each module and each plan day.

DIFFICULTY = {
    "vertical-hello": 1, "add-two": 1, "even-odd": 1, "countdown": 1, "reverse-word": 1, "count-vowels": 1,
    "fizzbuzz": 2, "largest": 1,
    "pf-units": 2, "pf-currency": 2, "kg-lb": 1, "file-extension": 2, "safe-divide": 2, "any-base": 3,
    "pf-time": 2, "pf-permille": 1, "compound-interest": 1, "days-between": 1, "weekday": 1,
    "pf-unique": 1, "pf-roman": 2, "unique-words": 2, "second-largest": 1, "letter-frequency": 2, "int-to-roman": 2,
    "pf-factors": 2, "pf-hanoi": 3, "pf-palprimes": 2, "is-prime": 2, "digital-root": 1, "hanoi-count": 2,
    "factorial-recursive": 2,
    "pf-sensor": 2, "pf-sports": 3, "max-temperature": 2, "poem-stats": 2, "class-averages": 3,
    "pf-caesar": 3, "caesar-decrypt": 2,
}

# ---------------------------------------------------------------- 7-day plan

PLAN = {
    "start": "2026-11-12",
    "days": [
        {"title": "Big recap: nine pre-final problems", "heavy": True, "time": "3 hours",
         "focus": "Redo the nine easier pre-final problems from a blank editor, easiest first. Before each submit, run through the checklist. Every time a test fails, write down why on the Notes page: that list drives the rest of the week. The three hardest (Tower of Hanoi, sports CSV, Caesar) come on days 5 and 6, after drills that build up to them.",
         "read": read("reference", "level-7"),
         "items": [f"pf-{x}" for x in ["units", "time", "currency", "permille", "unique", "sensor", "factors",
                                       "roman", "palprimes"]]},
        {"title": "Strings, slicing and errors", "time": "45 minutes",
         "focus": "Slicing by the right length, endswith, and catching ValueError. Then retry the two conversion problems.",
         "read": read("level-2", "level-7", "cat-text"),
         "items": ["kg-lb", "safe-divide", "any-base"], "retry": ["pf-units", "pf-currency"]},
        {"title": "Numbers and dates", "time": "45 minutes",
         "focus": "datetime format codes, total_seconds, and :.2f formatting.",
         "read": read("level-1", "cat-numbers", "cat-dates"),
         "items": ["days-between", "compound-interest"], "retry": ["pf-time", "pf-permille"]},
        {"title": "Lists, sets and dictionaries", "time": "45 minutes",
         "focus": "set for duplicates, dict counting with get, and building strings from a lookup table.",
         "read": read("level-4", "level-5", "cat-dicts"),
         "items": ["letter-frequency", "int-to-roman"], "retry": ["pf-unique", "pf-roman"]},
        {"title": "Loops and recursion", "time": "1.5 hours",
         "focus": "while loops that change n, square-root prime checks, and base cases. Warm up on factorial and the Hanoi move count, then do the full Tower of Hanoi for the first time.",
         "read": read("level-3", "level-6", "cat-loops"),
         "items": ["is-prime", "factorial-recursive", "hanoi-count", "pf-hanoi"], "retry": ["pf-factors", "pf-palprimes"]},
        {"title": "Files, CSV and ciphers", "time": "1.5 hours",
         "focus": "Skipping broken lines, csv.reader, sorting with key=, and ord/chr with % 26. Then the two hardest pre-final problems for the first time: sports CSV and Caesar.",
         "read": read("level-9", "level-10", "cat-files", "cat-convert"),
         "items": ["max-temperature", "class-averages", "caesar-decrypt", "pf-sports", "pf-caesar"], "retry": ["pf-sensor"]},
        {"title": "Mock final", "heavy": True, "time": "90 minutes, timed",
         "focus": "Six pre-final problems as a timed test. Press Clear on each one first so you start from a blank editor, and don't open the reference solutions until the 90 minutes are over.",
         "read": read("reference"),
         "items": ["pf-currency", "pf-time", "pf-roman", "pf-palprimes", "pf-sports", "pf-caesar"]},
    ],
}

CHECKLIST = [
    "Read the exact output format. Spaces, commas, `-->` vs `->`, and 2 decimals all matter.",
    "Test the examples, then the edge cases: `0`, negative numbers, very big or very small input, empty input.",
    "`=` assigns, `==` compares. Every `(` needs its `)`.",
    "Count slice lengths: `\"EUR\"` is 3 letters (`[:-3]`), `\"Euro\"` is 4 (`[:-4]`).",
    "Never use a bare `except:`. Use `except ValueError:`.",
    "Check format codes letter by letter: `%H` is the hour, `%G` is the ISO year.",
    "Compare numbers as numbers, not text: `\"$127 M\"` sorts below `\"$94 M\"` as strings.",
    "If the problem says the input is always correct, skip `try`/`except`.",
    "If the task names a file, open it by that exact name.",
]

# ---------------------------------------------------------------- build


def run(solution, stdin, files, override=None):
    with tempfile.TemporaryDirectory() as tmp:
        for name, content in {**{n: FILES[n] for n in files}, **(override or {})}.items():
            Path(tmp, name).write_text(content, encoding="utf-8", newline="\n")
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        out = subprocess.run([sys.executable, "-I", "-c", solution], input=stdin + "\n" if stdin else "",
                             capture_output=True, text=True, encoding="utf-8", cwd=tmp, env=env, timeout=30)
    if out.returncode != 0 or out.stderr:
        raise SystemExit(f"reference solution failed on input {stdin!r}:\n{out.stderr}")
    return "\n".join(line.rstrip() for line in out.stdout.split("\n")).rstrip("\n")


def balance_samples(tests):
    """About half the tests are shown as examples, the rest are hidden (at least one hidden when there are 2+)."""
    want = max(1, len(tests) // 2)
    for t in tests:
        if sum(x["sample"] for x in tests) >= want:
            break
        t["sample"] = True
    while len(tests) > 1 and all(t["sample"] for t in tests):
        next(t for t in reversed(tests) if t["sample"])["sample"] = False


def build():
    module_ids = {m["id"] for m in MODULES}
    ids = [p["id"] for p in P]
    assert len(ids) == len(set(ids)), "duplicate problem id"
    problems = []
    for p in P:
        assert p["module"] in module_ids, p["id"]
        files = p.get("files", [])
        tests = []
        for i, s, *override in p["tests"]:
            override = override[0] if override else None
            assert not override or set(override) <= set(files), f"{p['id']}: override for a file it doesn't use"
            t = {"input": i, "output": run(p["solution"], i, files, override), "sample": s}
            if override:
                t["files"] = override
            tests.append(t)
        balance_samples(tests)
        assert p["id"] in DIFFICULTY, f"{p['id']}: no difficulty"
        item = {k: v for k, v in p.items() if k != "tests"}
        item["difficulty"] = DIFFICULTY[p["id"]]
        item["tests"] = tests
        problems.append(item)
        print(f"  {p['id']}: {len(tests)} tests")
    assert set(DIFFICULTY) == set(ids) and set(DIFFICULTY.values()) <= {1, 2, 3}, "DIFFICULTY must cover every problem with 1-3"
    for day in PLAN["days"]:
        for pid in day["items"] + day.get("retry", []):
            assert pid in ids, f"plan refers to unknown problem {pid}"
        for key in ("items", "retry"):  # easiest first; sorted() is stable, so equal ones keep their order
            if key in day:
                day[key] = sorted(day[key], key=DIFFICULTY.get)
    module_order = [m["id"] for m in MODULES]
    order = {pid: n for n, pid in enumerate(ids)}
    problems.sort(key=lambda p: (module_order.index(p["module"]), p["difficulty"], order[p["id"]]))

    js = ("// Generated by tools/build_problems.py. Edit that file, then run it again.\n"
          f"export const modules = {json.dumps(MODULES, ensure_ascii=False, indent=1)};\n"
          f"export const files = {json.dumps(FILES, ensure_ascii=False)};\n"
          f"export const plan = {json.dumps(PLAN, ensure_ascii=False, indent=1)};\n"
          f"export const checklist = {json.dumps(CHECKLIST, ensure_ascii=False, indent=1)};\n"
          f"export const problems = {json.dumps(problems, ensure_ascii=False, indent=1)};\n")
    OUT.write_text(js, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(problems)} problems)")


if __name__ == "__main__":
    build()
