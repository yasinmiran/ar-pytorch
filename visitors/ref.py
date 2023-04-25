import ast
from typing import Dict, Set


class ReferenceExtractor(ast.NodeVisitor):
    def __init__(self):
        self.imports: Dict[str, str] = {}
        self.references: Set[str] = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in self.imports:
            self.references.add(self.imports[node.value.id])
        self.generic_visit(node)

