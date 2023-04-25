import ast
import importlib
import os
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule

from utils import to_json, is_valid_namespace, write_json_to_file
from visitors.clazz import ClassAnalyzer, ClassRelationshipAnalyzer, SuperclassFinder
from visitors.func import FunctionAnalyzer
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


def analyze(o):
    usages = check_class_usages(o)
    extends = check_superclasses(o)
    imports = check_module_imports(o)
    refs = [find_module_path(r) for r in check_referenced_modules(o)]
    return {
        **usages,
        "extends": extends,
        "imports": imports,
        "refs": refs,
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

    analyzer = FunctionAnalyzer(o["object_name"]) \
        if o["object_type"] == "Function" \
        else ClassAnalyzer(o["object_name"])

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
    return finder.superclass_names


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


def main():
    nodes, links, categories = [], [], []
    _namespaces = set()

    # first derive the namespaces from the given set.
    for p in set2:
        x = extract_namespaces(p)
        for xi in x:
            if is_valid_namespace(xi):
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
            if is_valid_namespace(i):
                _namespaces.add(i)

    # track the initial namespaces.
    category_id_count = 0
    for n in _namespaces:
        categories.append({"id": category_id_count, "name": n})
        category_id_count += 1

    node_id_count = 0

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
    }), "data/vis.json")

    write_json_to_file(to_json(targets), "data/data.json")


if __name__ == '__main__':
    main()
