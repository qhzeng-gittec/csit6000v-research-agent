

Based on `doc.txt`, the difference between a method and a function is as follows:

**Methods are tied to an object; functions stand alone.**

- **String methods** (like `.lower()` and `.upper()`) are special functions that come bundled with strings. They are written with a dot (.) at the beginning of their names — for example, `.lower()` is written with a leading dot instead of as `lower()`. The dot tells Python that what follows is the name of a method. This notation makes it easier to differentiate string methods from built-in functions like `print()` and `type()`.

- **Functions** (like `len()`) are stand-alone. If you want to determine the length of a string, you call the `len()` function directly, e.g., `len(name)`.

The key distinction, as the document puts it: `len()` is a stand-alone function that you call directly, whereas `.upper()` and `.lower()` **must be used in conjunction with a string — they do not exist independently**. For example, you tack `.lower()` onto the end of the string itself, as in `"Jean-Luc Picard".lower()` or `name.lower()`.