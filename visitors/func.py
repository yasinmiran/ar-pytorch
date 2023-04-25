import ast


class FunctionAnalyzer(ast.NodeVisitor):
    def __init__(self, target_function):
        self.target_function = target_function
        self.in_target_function = False
        self.used_classes = set()
        self.used_functions = set()
        self.used_constants = set()
        self.imported_modules = set()

    def visit_Import(self, node):
        if self.in_target_function:
            for alias in node.names:
                self.imported_modules.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if self.in_target_function:
            for alias in node.names:
                self.imported_modules.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name == self.target_function:
            self.in_target_function = True
            self.generic_visit(node)
            self.in_target_function = False

    def visit_Attribute(self, node):
        if self.in_target_function:
            self.used_classes.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.in_target_function:
            if isinstance(node.func, ast.Name):
                self.used_functions.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                self.used_functions.add(node.func.attr)
        self.generic_visit(node)

    def visit_NameConstant(self, node):
        if self.in_target_function:
            self.used_constants.add(node.value)
        self.generic_visit(node)

    def visit_Num(self, node):
        if self.in_target_function:
            self.used_constants.add(node.n)
        self.generic_visit(node)

    def visit_Str(self, node):
        if self.in_target_function:
            self.used_constants.add(node.s)
        self.generic_visit(node)
