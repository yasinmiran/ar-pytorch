import ast
import importlib
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule

set2 = [
    "torch.utils.checkpoint.CheckpointFunction",
    "torch.autograd.function._SingleLevelFunction",
    "torch.autograd.function.Function",
    "torch.nn.modules.activation.ReLU",
    "torch.nn.modules.activation.Threshold",
    "torch.nn.modules.conv._Convnd",
    "torch.nn.modules.conv.Conv1d",
    "torch.nn.modules.conv.Conv2d",
    "torch.nn.modules.conv.Conv3d",
    "torch.nn.functional.relu",
    "torch.nn.functional.threshold",
    "torch._tensor.Tensor",
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

    private_classes = []
    private_functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('_'):
            private_classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) and node.name.startswith('_'):
            private_functions.append(node.name)

    return private_classes, private_functions


# figure out the type of the target object
def identify_object_type(package_path):
    module_path, obj_name = package_path.rsplit('.', 1)

    try:
        module = importlib.import_module(module_path)
        if str(obj_name).startswith("_"):
            clzzes, funcs = find_private_top_level_members(module.__file__)
            print(clzzes, funcs)
            return "Class" if len(clzzes) > 0 else "Function"
        else:
            obj = getattr(module, obj_name)
            if isclass(obj):
                return "Class"
            elif isfunction(obj):
                return "Function"
            elif ismethod(obj):
                return "Method"
            elif isbuiltin(obj):
                return "Builtin Function or Method"
            elif ismodule(obj):
                return "Module"
            else:
                return "Unknown"
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error: {e}")
        return None


if __name__ == '__main__':
    for p in set2:
        print(identify_object_type(p))

    # file_path = sys.argv[1]  # Replace with your file path or pass it as a command-line argument
    # imported_modules = find_imports(file_path)
    # print(f"Modules imported in {file_path}: {imported_modules}")

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
