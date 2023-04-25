import ast
import importlib
import json
import os
import pprint
import re
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule

from visitors.clazz import ClassAnalyzer, ClassRelationshipAnalyzer, SuperclassFinder
from visitors.imports import ImportCollector
from visitors.ref import ReferenceExtractor

set2 = [
    "torch",
    "torch.utils.checkpoint.CheckpointFunction",
    "torch.autograd.function._SingleLevelFunction",
    "torch.autograd.function.Function",
    "torch.nn.modules.activation.ReLU",
    "torch.nn.modules.activation.Threshold",
    "torch.nn.modules.conv._ConvNd",
    "torch.nn.modules.conv.Conv1d",
    "torch.nn.modules.conv.Conv2d",
    "torch.nn.modules.conv.Conv3d",
    "torch.nn.functional.relu",
    "torch.nn.functional.threshold",
    "torch._tensor.Tensor",
]


# find the
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


def analyze(o):
    usages = check_class_usages(o)
    _, extends = check_superclasses(o)
    imports = check_module_imports(o)
    refs = check_referenced_modules(o)

    paths = []
    for r in refs:
        paths.append(find_module_path(r))

    return {
        **usages,
        "extends": extends,
        "imports": imports,
        "refs": paths
    }


def find_module_path(module_name):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None

    if module is None or not hasattr(module, "__file__"):
        return None

    return os.path.abspath(module.__file__)


def check_class_usages(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    ast.fix_missing_locations(tree)  # Fix missing parent/child relationships

    # Assign parent references to all nodes
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    analyzer = ClassAnalyzer(o["object_name"])
    analyzer.visit(tree)

    return {
        'classes': analyzer.used_classes,
        'functions': analyzer.used_functions,
        'constants': analyzer.used_constants,
        'modules': analyzer.imported_modules,
    }


def check_class_relationship(file_path, base_class, target_class):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    analyzer = ClassRelationshipAnalyzer(base_class, target_class)
    analyzer.visit(tree)

    return {
        'extends': analyzer.extends_base_class,
        'uses': analyzer.uses_base_class,
    }


def check_superclasses(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    finder = SuperclassFinder(o["object_name"])
    finder.visit(tree)
    return finder.has_superclass, finder.superclass_names


def check_module_imports(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    collector = ImportCollector()
    collector.visit(tree)
    return collector.imported_modules


def check_referenced_modules(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    extractor = ReferenceExtractor()
    extractor.visit(tree)

    return extractor.references


def generate_metadata(package_path):
    if "." in package_path:
        module_path, obj_name = package_path.rsplit('.', 1)
    else:
        module_path, obj_name = package_path, package_path
    metadata = {}
    try:
        module = importlib.import_module(module_path)
        obj = getattr(module, obj_name)

        object_type = "Unknown"

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

        metadata["object_name"] = obj_name
        metadata["object_type"] = object_type
        metadata["abs_file_path"] = str(module.__file__)
        metadata["module_name"] = str(module.__name__)
        return metadata

    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error: {e}")
        return None


def write_json_to_file(json_obj, file_name):
    with open(file_name, 'w') as f:
        json.dump(json_obj, f)


def convert_sets_to_lists(data):
    if isinstance(data, dict):
        return {k: convert_sets_to_lists(v) for k, v in data.items()}
    elif isinstance(data, set):
        return list(data)
    elif isinstance(data, (list, tuple)):
        return [convert_sets_to_lists(item) for item in data]
    else:
        return data


def match_string_within_string(string, pattern):
    matches = re.findall(pattern, string)
    return matches


if __name__ == '__main__':
    targets = {}
    for p in set2:
        meta = generate_metadata(p)
        data = analyze(meta)
        targets = {
            **targets,
            p: data
        }
    pprint.pprint(targets)

    # refs = targets["torch.utils.checkpoint.CheckpointFunction"]["refs"]
    #
    # filtered_paths = []
    # for r in refs:
    #     if match_string_within_string(r, "site-packages/torch/"):
    #         filtered_paths.append(r)
    #
    # for p in filtered_paths:
    #     meta = generate_metadata(p)
    #     data = analyze(meta)
    #     targets = {
    #         **targets,
    #         p: data
    #     }

    # print(filtered_paths)

    write_json_to_file(convert_sets_to_lists(targets), "data.json")

    #
    # labels = list(data.keys())
    # values = list(data.values())
    #
    # fig, ax = plt.subplots()
    # # Create the bar chart
    # ax.bar(labels, values)
    # # Add labels and a title
    # ax.set_ylabel('Frequency')
    # ax.set_xlabel('Element')
    # ax.set_title('Element Frequencies')
    #
    # # Display the bar chart
    # plt.show()

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
