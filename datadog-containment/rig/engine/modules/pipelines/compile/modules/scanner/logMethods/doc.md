---
icon: material/math-log
---

Defines function names that mark string constants as having a [log](https://doc.log10x.com/run/transform/symbol/#log) context.

When parsing these invocations:
``` cpp
logger.error("could not connect to {}", host);
cerr << "could not connect to" << host << << std::endl;
```

The string constants receive a 'log' context. So does every literal in a method that logs, throws or raises (in Java source, Python and Scala, only those preceding the logging or throwing statement), and any literal carrying a format placeholder. A literal in a method that does neither keeps a 'const' context:
``` js
foo("could not connect to " + host);
```

Use the [symbolTypes](https://doc.log10x.com/compile/link/#symboltypes) argument to filter non-logging symbols and reduce library file size. 
