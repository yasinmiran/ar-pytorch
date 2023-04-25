import ast


class ImportCollector(ast.NodeVisitor):
    def __init__(self):
        self.imported_modules = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imported_modules.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.imported_modules.add(node.module)
        self.generic_visit(node)
