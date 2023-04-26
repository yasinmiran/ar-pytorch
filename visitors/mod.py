import ast


class ModuleAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.top_level_functions = []
        self.top_level_classes = []

    def visit_FunctionDef(self, node):
        self.top_level_functions.append(node.name)
        # Do not call generic_visit to avoid analyzing inner functions

    def visit_AsyncFunctionDef(self, node):
        self.top_level_functions.append(node.name)
        # Do not call generic_visit to avoid analyzing inner async functions

    def visit_ClassDef(self, node):
        self.top_level_classes.append(node.name)
        # Do not call generic_visit to avoid analyzing inner classes
