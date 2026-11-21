According to `doc.txt`, the difference is that methods are special functions that come bundled with strings and must be used in conjunction with a string, whereas functions like `len()` are stand-alone and called directly.

Specifically, the document says:

- "Strings come bundled with special functions called string methods that you can use to work with and manipulate strings." (doc.txt)
- "The dot (.) tells Python that what follows is the name of a method—the lower() method in this case." (doc.txt)
- "We’ll refer to string methods with a dot (.) at the beginning of their names. For example, .lower() is written with a leading dot instead of as lower(). This makes it easier to differentiate functions that are string methods from built-in functions like print() and type()." (doc.txt)
- "len() is a stand-alone function. If you want to determine the length of the name string, then you call the len() function directly." (doc.txt)
- "On the other hand, .upper() and .lower() must be used in conjunction with a string. They do not exist independently." (doc.txt)

So, in the document's terms: a method is a string-bundled function written with a leading dot that does not exist independently, while a function such as `len()` is stand-alone and called directly.