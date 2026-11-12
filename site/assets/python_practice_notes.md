# Python Pre-Final Practice: Problems, Misses, and Solutions

Notes from a 12-problem practice test. Each problem has what it asks, what went wrong or was easy to miss, and a clean solution with no comments.

The solutions were worked out in chat. Re-run them on the platform's tests before trusting them. Problem 4 has a hidden-test failure that was never resolved.

---

## Quick checklist before submitting anything

- Read the exact output format. Spaces, commas, `-->` vs `->`, and `2` decimals all matter.
- Test with the examples by hand. Then test the edge cases: `0`, negative numbers, very big or very small input, empty input.
- Check that `=` (assign) is not `==` (compare), and that every `(` has its `)`.
- Count slice lengths. `"EUR"` has 3 letters, so use `[:-3]`. `"Euro"` has 4, so use `[:-4]`.
- Never use a bare `except:`. Use `except ValueError:`.
- Check format codes letter by letter. `%H` is the hour, but `%G` is the ISO year.
- Compare numbers as numbers, not as text. `"$127 M"` sorts below `"$94 M"` as strings.
- If the problem says "the input is always correct", skip `try`/`except`.
- If the test names a file, open it by the exact name given.

---

## 1. Unit conversion: meters and feet

**Task:** input like `123m` or `99.9876543ft`. Convert using 1 m = 3.2808 ft. Print 2 decimals plus the unit. Print `format error` for bad input.

**What was missed:**
- Typos: `for y in x` instead of `for i in x`, `oor` instead of `or`, and `i == "0"` (compare) where assignment was meant.
- The wrong factor, `3.808` instead of `3.2808`.
- `-0ft` printed `-0.00m`. `float("-0")` is negative zero, but `int("-0")` is just `0`.
- `-0xabcdm` printed `format error`. `float()` can't read hex, but `int(text, 0)` reads `0x`, `0b` and `0o`.

**Required ideas:** `endswith`, slicing, try `int(num, 0)` first and fall back to `float(num)`, f-string `:.2f`, `except ValueError`.

```python
x = input().strip()

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
```

---

## 2. Time difference in minutes

**Task:** input `2019-12-19 17:18:20,2019-12-20 19:18:20`. Print the absolute difference in whole minutes.

**What was missed:**
- A format typo: `%G` instead of `%H` crashed `strptime` with a `ValueError`.
- `.seconds` ignores whole days, so use `.total_seconds()`.
- Forgetting `abs()` when the times can be in either order.

**Required ideas:** `datetime.strptime`, `timedelta`, `total_seconds()`, `abs`, `// 60`.

```python
from datetime import datetime

a, b = input().split(",")
fmt = "%Y-%m-%d %H:%M:%S"

t1 = datetime.strptime(a.strip(), fmt)
t2 = datetime.strptime(b.strip(), fmt)

seconds = abs((t2 - t1).total_seconds())
print(int(seconds // 60))
```

---

## 3. Currency conversion: RMB, CNY, Euro, EUR

**Task:** input like `123RMB` or `999EUR`. Convert with a rate of 7.8942 and print 2 decimals. The output uses the same naming style as the input. Names map to names (`RMB` to `Euro`, `Euro` to `RMB`). Symbols map to symbols (`CNY` to `EUR`, `EUR` to `CNY`). Bad input prints `format error`.

**What was missed:**
- Hardcoding the output (`CNY` for every Euro input) breaks the name-to-name and symbol-to-symbol rule.
- Only handling `RMB` and `Euro`, not `CNY` and `EUR`.
- A wrong slice length on line 10 (`[:-4]` on `"EUR"` cut off a digit, so `999EUR` became `99`).
- A bare `except:`.

**Required ideas:** one variable for which currency came in, another for what text to print. Check slice lengths carefully.

```python
money = input().strip()

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
```

---

## 4. Per mille growth (UNRESOLVED hidden test)

**Task:** input `N` (per mille, so N/1000). Working hard multiplies by `(1 + N/1000)` each day, and slacking multiplies by `(1 - N/1000)`. After 365 days print `up, down, ratio`. The powers have 2 decimals and the ratio is a whole number. Sample `1` gives `1.44, 0.69, 2`.

**What was missed:**
- A missing `=` (`up ( 1 + ...` is a `NameError`).
- The sample passed but a hidden test failed. The cause was never found.

**Things to try if a hidden test fails (in this order):**
1. Round the ratio instead of truncating: `round(up / down)`.
2. Compute the ratio from the rounded powers: `up = round(..., 2)` and `down = round(..., 2)`.
3. Check whether the ratio should print with a different format.

The sample (`N = 1`) can't tell these options apart. A larger `N` gives very different ratios.

```python
n = float(input())

up = (1 + n / 1000) ** 365
down = (1 - n / 1000) ** 365

print(f"{up:.2f}, {down:.2f}, {int(up / down)}")
```

---

## 5. Count different values in a list

**Task:** input `[0, 1, 2, 3, 4, 4.0, 4.00, 3, 2, 1, 0]`. Print how many different values there are (`5` here).

**Required ideas:** `eval(input())` turns the typed text into a list. `4`, `4.0` and `4.00` are equal in Python, so duplicates collapse. The short version is `print(len(set(eval(input()))))`. The longer loop version is below.

```python
lst = eval(input())

unique = []
for item in lst:
    if item not in unique:
        unique.append(item)

count = len(unique)
print(count)
```

---

## 6. Average of the light sensor from a file

**Task:** read `sensor-data-1k.txt` (1000 lines: date, time, temperature, humidity, light, voltage). Print the average light value with 2 decimals.

**Required ideas:** `open(..., "r")`, loop over lines, `split()`, light is index 4 (the 5th piece), skip lines that don't have 6 pieces, divide the total by the count, `:.2f`.

```python
f = open("sensor-data-1k.txt", "r")

total = 0
count = 0

for line in f:
    parts = line.split()
    if len(parts) == 6:
        total = total + float(parts[4])
        count = count + 1

f.close()

print(f"{total / count:.2f}")
```

---

## 7. Prime factor decomposition

**Task:** input a positive integer `n`. Print a list of its prime factors, for example `12` gives `[2, 2, 3]`.

**Required ideas:** start the divisor at 2. Divide while it fits, then move to the next divisor. Use `//` so `n` stays an integer. You don't need to test whether the divisor is prime, because smaller primes were already divided out.

```python
n = int(input())

factors = []
d = 2

while n > 1:
    while n % d == 0:
        factors.append(d)
        n = n // d
    d = d + 1

print(factors)
```

---

## 8. Roman numerals to an integer

**Task:** input a legal Roman numeral (1 to 3999). Print the integer, for example `MCMIV` gives `1904`.

**Required ideas:** a dictionary of the 7 single letters. If a letter is smaller than the next one, subtract it. Otherwise add it. This covers IV, IX, XL, XC, CD and CM without listing them. Check `i + 1 < len(s)` so the last letter doesn't look past the end.

```python
s = input().strip()

values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

total = 0
for i in range(len(s)):
    if i + 1 < len(s) and values[s[i]] < values[s[i + 1]]:
        total = total - values[s[i]]
    else:
        total = total + values[s[i]]

print(total)
```

---

## 9. Tower of Hanoi

**Task:** write `move(n, a, b, c)`. Input is `n` on one line and `A B C` on the next. Print each move like `A --> B`.

**Required ideas:** recursion with a base case. Move `n-1` disks from `a` to `b` (using `c`). Print the move from `a` to `c`. Move `n-1` disks from `b` to `c` (using `a`). The problem text shows `->` but the example box shows `-->`. Follow the example box, and check which one the tests want.

```python
def move(n, a, b, c):
    if n == 0:
        return
    move(n - 1, a, c, b)
    print(a, "-->", c)
    move(n - 1, b, a, c)

n = int(input())
a, b, c = input().split()
move(n, a, b, c)
```

---

## 10. Palindromic primes

**Task:** input `n`. Print the smallest `n` palindromic primes separated by spaces. For `10` the output is `2 3 5 7 11 101 131 151 181 191`.

**Required ideas:** a helper `is_prime` that tests divisors only up to the square root. A palindrome check with `s == s[::-1]`. Count up with a `while` loop until you have `n` results. Print with `" ".join(...)`. The problem text shows commas but the example uses spaces, so follow the example.

```python
def is_prime(x):
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
```

---

## 11. Sports income ranking (CSV)

**Task:** read `2012-19sport.csv` with columns Rank, Name, Pay, Salary/Wins, Endorsement, Sport, Year. Money looks like `$93.4 M`.
- If the first input is a year from 2012 to 2019, the second input is `k`. Print the top `k` athletes by pay for that year, one per line, separated by ` | `. If `k` is bigger than the number of athletes, print them all.
- If the first input is `sport` (any case), the second input is the year and the third is a sport index. Print the sports list for that year in ascending order as `1: Auto Racing`. Then print that sport's athletes and `TOTAL: $607.00 M`.
- Anything else prints `Wrong Input`.

**What was easy to miss:**
- Skip the header row.
- Strip the `#` from the rank (`#1` becomes `1`) to match the expected output.
- Convert money to a number before sorting. As strings, `$127 M` sorts below `$94 M`.
- Slicing `[:k]` handles "k too big" by itself.
- Sport indexes start at 1. Use `sorted(set(...))` for the list.
- The `Wrong Input` rule covers both a year outside the range and any other text.
- Encoding: if it crashes or `Sánchez` looks garbled, try `encoding="gbk"`.
- Endorsement values can end in `K` (`$150 K`), so the money helper handles that too.

```python
import csv

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
```

---

## 12. Text analysis and Caesar encryption

**Task:** read `info.txt` using the given `read_file` function. The input is a secret word (a weekday). Print, in order:
1. Counts of uppercase, lowercase, digits, whitespace, and other characters, separated by spaces.
2. `A total of N words.` Replace all punctuation with spaces, `split()`, and count.
3. The shift: the sum of the ASCII values of the secret word, modulo 26. For `Tuesday` it is 735 % 26 = 7.
4. The file's text encrypted with the Caesar cipher.

**What was easy to miss:**
- Whitespace includes `\n` and `\t`, not just spaces (`isspace()`).
- Hyphenated words split in two (`Asia-Pacific` is 2 words) because the hyphen is punctuation.
- Letters wrap around (`z` to `a`) with `% 26`. Case is preserved. Non-letters are copied unchanged.
- The example output in the problem shows the stats block twice. The second block fits the real file, so the first is probably stale. If the tests fail on format, check this first.

```python
import string

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
```

---

## Skills to practice from this set

| Skill | Problems |
|---|---|
| String slicing and `endswith` | 1, 3 |
| `try` / `except ValueError` | 1, 3 |
| f-strings and `:.2f` | 1, 3, 4, 6, 11 |
| `datetime` and format codes | 2 |
| Lists, `set`, `in` | 5, 11 |
| File reading and `split()` | 6, 11, 12 |
| Loops and `while` | 6, 7, 10 |
| Dictionaries | 8 |
| Recursion | 9 |
| Helper functions | 10, 11 |
| `csv` module and sorting with `key=` | 11 |
| `string` module and `ord`/`chr` | 12 |
