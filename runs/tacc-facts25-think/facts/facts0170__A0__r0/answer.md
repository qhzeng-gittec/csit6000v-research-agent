

Based on `doc.txt`, the difference between a method and a function is as follows:

- **Functions** (like `len()`, `print()`, and `type()`) are **stand-alone** — they can be called directly and independently. For example, to get the length of a string, you simply call `len(name)` directly.

- **Methods** (like `.upper()` and `.lower()`) **must be used in conjunction with an object** (in this case, a string). They "do not exist independently" — they are tacked onto the end of the string itself, e.g., `name.upper()`.

The document also notes a notational convention to make this distinction easier: string methods are written with a **leading dot** (e.g., `.lower()`), which differentiates them from built-in functions like `print()` and `type()`.

In short, per the document: a function is stand-alone and called directly, while a method is attached to and used together with a specific object (a string, in this case).