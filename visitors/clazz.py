import ast


class ClassAnalyzer(ast.NodeVisitor):

    def __init__(self, target_class):
        self.target_class = target_class
        self.in_target_class = False
        self.used_classes = set()
        self.used_functions = set()
        self.used_constants = set()
        self.imported_modules = set()

    def visit_ClassDef(self, node):
        if node.name == self.target_class:
            self.in_target_class = True
            self.generic_visit(node)
            self.in_target_class = False
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if self.in_target_class:
            if not node.name.startswith("__"):
                self.used_functions.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.in_target_class and isinstance(node.func, ast.Name):
            self.used_functions.add(node.func.id)
        self.generic_visit(node)

    def visit_Import(self, node):
        if self.in_target_class:
            for alias in node.names:
                self.imported_modules.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if self.in_target_class:
            self.imported_modules.add(node.module)
            for alias in node.names:
                name = alias.name
                if name[0].isupper():  # Class names start with an uppercase letter
                    self.used_classes.add(name)
        self.generic_visit(node)

    def visit_Name(self, node):
        if self.in_target_class and isinstance(node.ctx, ast.Load):
            if node.id[0].isupper():  # Class names start with an uppercase letter
                self.used_classes.add(node.id)
            elif node.id.isupper():  # Constants are usually all uppercase
                self.used_constants.add(node.id)
        self.generic_visit(node)


class ClassRelationshipAnalyzer(ast.NodeVisitor):
    def __init__(self, base_class, target_class):
        self.base_class = base_class
        self.target_class = target_class
        self.extends_base_class = False
        self.uses_base_class = False

    def visit_ClassDef(self, node):
        if node.name == self.target_class:
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == self.base_class:
                    self.extends_base_class = True

            self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == self.base_class:
            self.uses_base_class = True
        self.generic_visit(node)


class SuperclassFinder(ast.NodeVisitor):

    def __init__(self, target_class):
        self.target_class = target_class
        self.has_superclass = False
        self.superclass_names = []

    def visit_ClassDef(self, node):
        if node.name == self.target_class:
            self.has_superclass = True
            for base in node.bases:
                if isinstance(base, ast.Name):
                    self.superclass_names.append(base.id)
                elif isinstance(base, ast.Attribute):
                    # self.superclass_names.append(f"{base.value.id}.{base.attr}")
                    self.superclass_names.append(base.attr)
            for keyword in node.keywords:
                if keyword.arg == "metaclass":
                    if isinstance(keyword.value, ast.Name):
                        # self.superclass_names.append(f"metaclass={keyword.value.id}")
                        self.superclass_names.append(keyword.value.id)
                    elif isinstance(keyword.value, ast.Attribute):
                        # self.superclass_names.append(f"metaclass={keyword.value.value.id}.{keyword.value.attr}")
                        self.superclass_names.append(keyword.value.attr)
