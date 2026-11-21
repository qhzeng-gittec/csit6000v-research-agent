

According to `doc.txt`, the difference is:

- **Methods** are special functions that come bundled with strings (e.g., `.lower()`, `.upper()`). They are written with a leading dot (e.g., `.lower()` instead of `lower()`), and the dot tells Python that what follows is the name of a method. Crucially, methods "must be used in conjunction with a string. They do not exist independently."

- **Functions** like `len()` are stand-alone. You call them directly (e.g., `len(name)`), without attaching them to a string.

The document notes that this leading-dot notation makes it easier to differentiate functions that are string methods from built-in functions like `print()` and `type()`.