import ast
import importlib
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule

from analyzers.clazz import ClassAnalyzer, ClassRelationshipAnalyzer, SuperclassFinder

set2 = [
    # "torch.utils.checkpoint.CheckpointFunction",
    # "torch.autograd.function._SingleLevelFunction",
    # "torch.autograd.function.Function",
    # "torch.nn.modules.activation.ReLU",
    # "torch.nn.modules.activation.Threshold",
    "torch.nn.modules.conv._Convnd",
    "torch.nn.modules.conv.Conv1d",
    "torch.nn.modules.conv.Conv2d",
    "torch.nn.modules.conv.Conv3d",
    # "torch.nn.functional.relu",
    # "torch.nn.functional.threshold",
    # "torch._tensor.Tensor",
]


def find_imports(path):
    with open(path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imports.append(alias.name)

    return imports


# find the protected members of the target file
def find_private_top_level_members(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)

    private_classes = set()
    private_functions = set()

    # note that we transform the node names to lowercase
    # because at this point we're only interested in matching
    # an exact identifier.
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('_'):
            private_classes.add(node.name.lower())
        elif isinstance(node, ast.FunctionDef) and node.name.startswith('_'):
            private_functions.add(node.name.lower())

    return private_classes, private_functions


def analyze_class_usages(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    analyzer = ClassAnalyzer("Conv1d")
    analyzer.visit(tree)

    return {
        'classes': analyzer.used_classes,
        'functions': analyzer.used_functions,
        'constants': analyzer.used_constants,
        'modules': analyzer.imported_modules,
    }


def analyze_class_relationship(file_path, base_class, target_class):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    analyzer = ClassRelationshipAnalyzer(base_class, target_class)
    analyzer.visit(tree)

    return {
        'extends': analyzer.extends_base_class,
        'uses': analyzer.uses_base_class,
    }


def has_superclass(file_path, target_class):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    finder = SuperclassFinder(target_class)
    finder.visit(tree)
    return finder.has_superclass


def get_meta_data(package_path):
    module_path, obj_name = package_path.rsplit('.', 1)
    meta = {}
    try:
        module = importlib.import_module(module_path)
        object_type = "Unknown"
        if str(obj_name).startswith("_"):
            meta["is_protected"] = True
            classes, funcs = find_private_top_level_members(module.__file__)
            if str(obj_name).lower() in classes:
                object_type = "Class"
            elif str(obj_name).lower() in funcs:
                object_type = "Function"
        else:
            meta["is_protected"] = False
            obj = getattr(module, obj_name)
            if isclass(obj):
                object_type = "Class"
            elif isfunction(obj):
                object_type = "Function"
            elif ismethod(obj):
                object_type = "Method"
            elif isbuiltin(obj):
                object_type = "Builtin Function or Method"
            elif ismodule(obj):
                object_type = "Module"
        meta["object_type"] = object_type
        meta["abs_file_path"] = module.__file__
        meta["module_name"] = module.__name__
        return meta
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error: {e}")
        return None


if __name__ == '__main__':
    for p in set2:
        meta = get_meta_data(p)
        print(analyze_class_usages(meta))

# Python dependencies required for development
# astunparse
# expecttest
# hypothesis
# numpy
# psutil
# pyyaml
# requests
# setuptools
# types-dataclasses
# typing-extensions
# sympy
# filelock
# networkx
# jinja2
# fsspec
