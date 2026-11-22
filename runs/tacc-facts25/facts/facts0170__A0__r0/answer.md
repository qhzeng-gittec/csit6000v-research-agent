Based on `doc.txt`, the difference between a method and a function is how they are used:

- **Functions** (like `len()`, `print()`, `type()`) are stand-alone. They can be called directly and exist independently. For example, to determine the length of a string, you call `len(name)` directly.

- **Methods** (like `.upper()` and `.lower()`) are special functions bundled with strings that must be used in conjunction with a string—they do not exist independently. They are written with a leading dot (e.g., `.lower()` instead of `lower()`), and the dot tells Python that what follows is the name of a method. This leading-dot notation makes it easier to differentiate string methods from built-in functions like `print()` and `type()`.