

Based on `doc.txt`, the difference is in how they are used:

- **Methods** are "special functions called string methods" that are bundled with strings. They are written with a leading dot — "We'll refer to string methods with a dot (.) at the beginning of their names. For example, .lower() is written with a leading dot instead of as lower()." This "makes it easier to differentiate functions that are string methods from built-in functions like print() and type()."

- **Functions** like `len()` are stand-alone: "len() is a stand-alone function. If you want to determine the length of the name string, then you call the len() function directly."

The document states the key distinction explicitly: "the important distinction here is how they're used." While `len()` is called directly, ".upper() and .lower() must be used in conjunction with a string. They do not exist independently."