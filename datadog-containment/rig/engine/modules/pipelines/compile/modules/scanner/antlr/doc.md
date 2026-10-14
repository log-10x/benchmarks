---
icon: material/file-code
---

Extracts [symbols](https://doc.log10x.com/run/transform/structure/#symbols) from source files using [ANTLR](http://www.antlr.org) parsers.

The [rules](https://doc.log10x.com/compile/scanner/antlr/rules/) for each [language](https://doc.log10x.com/compile/scanner/antlr/langs/) control which symbols to extract from the AST and their [context](https://doc.log10x.com/run/transform/symbol/#contexts) within the source file (e.g. class name, constant, enum,..). This enables generating symbol units from source code in virtually any programming language for which a [grammar](https://github.com/antlr/grammars-v4) is defined.

### :material-toy-brick-outline: Extensibility

Parsing source code files for a given language can be done by:

- Compiling a [g4 grammar](https://github.com/antlr/grammars-v4) file
  using the ANTLR [tool](https://www.antlr.org/download.html) into a parser class file and specifying its fully qualified class name via the [antlrParserClass](https://doc.log10x.com/compile/scanner/antlr/langs/#antlrparserclass) argument.

- Loading a .g4 grammar file directly via the [antlrGrammarFile](https://doc.log10x.com/compile/scanner/antlr/langs/#antlrgrammarfile) argument, assuming the target grammar does not require any language-specific code extensions.

The ANTLR scanner uses either pre-compiled or interpreted (.g4) parsers
to read the contents of input files and iterate their [AST](https://en.wikipedia.org/wiki/Abstract_syntax_tree). 

To learn more see the [ANTLR tutorial](https://tomassetti.me/antlr-mega-tutorial).

