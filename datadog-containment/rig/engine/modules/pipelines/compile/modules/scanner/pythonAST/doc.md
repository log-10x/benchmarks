---
icon: material/language-python
---

Extracts [symbol](https://doc.log10x.com/run/transform/structure/#symbols) values from `.py` files using Python's native AST parser via [astpretty](https://github.com/asottile/astpretty).

When no Python runtime is available, set [pythonPath](#pythonpath) to empty/null to fall back to [ANTLR python](https://doc.log10x.com/compile/scanner/antlr/#python) parsing.

 