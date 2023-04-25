import ast
import builtins
import importlib
import json
import os
import re
import sys
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule

from visitors.clazz import ClassAnalyzer, ClassRelationshipAnalyzer, SuperclassFinder
from visitors.imports import ImportCollector
from visitors.ref import ReferenceExtractor

set2 = [
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
namespaces = [
    "torch",
    "torch.utils",
    "torch.utils.checkpoint",
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
        "refs": paths,
        "meta": o
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


def to_json(data):
    if isinstance(data, dict):
        return {to_json(k): to_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [to_json(elem) for elem in data]
    elif isinstance(data, tuple):
        return tuple(to_json(elem) for elem in data)
    elif isinstance(data, set):
        return [to_json(elem) for elem in data]
    elif isinstance(data, str):
        return data.encode('unicode_escape').decode()
    elif isinstance(data, bytes):
        return data.decode('unicode_escape')
    elif isinstance(data, (int, float, bool, type(None))):
        return data
    else:
        return str(data)


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


def extract_namespaces(target):
    if "." in target:
        parts = target.split('.')
        namespaces = []
        for i in range(len(parts) - 1):
            namespace = '.'.join(parts[:i + 1])
            namespaces.append(namespace)
        return namespaces
    else:
        return [target]


def create_node(nodes, node_id_count, name, category_id):
    nodes.append({
        "id": node_id_count,
        "name": name,
        "label": {
            "normal": {
                "show": True
            }
        },
        "category": category_id
    })


def is_builtin(module_name: str) -> bool:
    if module_name in sys.builtin_module_names:
        return True
    if module_name in sys.modules:
        module = sys.modules[module_name]
        return module.__name__ in sys.builtin_module_names or \
            module.__name__ == builtins.__name__
    return False


def is_standard_library(module_name: str) -> bool:
    if module_name is None or module_name.startswith('.'):
        return False
    if module_name in sys.builtin_module_names:
        return True
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        return False

    module_file = getattr(module, "__file__", None)

    if module_file is None:
        return False

    return module_file.startswith(os.path.dirname(os.__file__))


def main():
    nodes = []
    links = []
    categories = []
    node_id_count = 0

    # namespaces are the categories
    _namespaces = set()

    # first derive the namespaces from the given set.
    for p in set2:
        x = extract_namespaces(p)
        for xi in x:
            if xi is not None and xi != "null" and \
                    not is_builtin(xi) and not is_standard_library(xi):
                _namespaces.add(xi)

    targets = {}

    # then we iterate through each of the
    # target class/function/namespace.
    for p in set2:
        data = analyze(generate_metadata(p))
        targets = {
            **targets,
            p: data
        }

    # create the node for ech namespaces with the imports.
    for key, value in targets.items():
        for i in targets[key]["imports"]:
            if i is not None and i != "null" and not is_builtin(i) \
                    and not is_standard_library(i):
                _namespaces.add(i)

    # track the initial namespaces.
    category_id_count = 0
    for n in _namespaces:
        categories.append({"id": category_id_count, "name": n})
        category_id_count += 1

    for namespace in _namespaces:
        create_node(nodes, node_id_count, namespace, namespace)
        node_id_count += 1

    links_count = 0

    # create the actual node.
    # i.e., torch.nn.modules.activation.Threshold x12 nodes
    for key, value in targets.items():
        create_node(nodes, node_id_count, key, category_id=targets[key]["meta"]["module_name"])
        for _import in targets[key]["imports"]:
            for category_index, category in enumerate(categories):
                if _import == category["name"]:
                    links.append({
                        "id": links_count,
                        "source": node_id_count,
                        "target": category_index
                    })
                    links_count += 1
        node_id_count += 1

    write_json_to_file(to_json({
        "nodes": nodes,
        "links": links,
        "categories": categories
    }), "vis.json")

    write_json_to_file(to_json(targets), "data.json")


if __name__ == '__main__':
    main()

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
