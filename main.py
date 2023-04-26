import ast
import importlib
import os
from inspect import isclass, isfunction, ismethod, isbuiltin, ismodule
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from torch.nn.modules import linear

from utils import to_json, is_valid_namespace, write_json_to_file
from visitors.clazz import ClassAnalyzer, ClassRelationshipAnalyzer, SuperclassFinder
from visitors.func import FunctionAnalyzer
from visitors.imports import ImportCollector
from visitors.mod import ModuleAnalyzer
from visitors.ref import ReferenceExtractor

app = FastAPI()

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
    import_statements, modules = check_module_imports(o)
    modules = check_modules(modules)
    refs = [find_module_path(r) for r in check_referenced_modules(o)]

    def find_module_by_name(name):
        for m in modules:
            if m["import_identifier"] == name:
                return m

    filtered_imports = set()
    for i in import_statements:
        mod = find_module_by_name(i)
        if mod is not None:
            a, b = set(mod["classes"]), set(usages["classes"])
            c = b.intersection(a)
            if c is not None and len(c) > 0:
                filtered_imports.add(i)
        else:
            filtered_imports.add(i)

    return {
        **usages,
        "extends": extends,
        "imports": filtered_imports,
        "module_info": modules,
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


def check_modules(modules):
    mods = []
    for m in modules:
        with open(m["abs_file_path"], 'r', encoding='utf-8') as file:
            file_content = file.read()
        tree = ast.parse(file_content)
        ast.fix_missing_locations(tree)
        analyzer = ModuleAnalyzer()
        analyzer.visit(tree)
        mods.append({
            "import_identifier": f"{m['module_name']}.{m['object_name']}",
            "module_name": m["module_name"],
            "object_name": m["object_name"],
            "classes": analyzer.top_level_classes,
            "functions": analyzer.top_level_functions,
        })
    return mods


def check_class_usages(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    ast.fix_missing_locations(tree)  # Fix missing parent/child relationships

    # Assign parent references to all nodes
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    if o["object_type"] == "Function":
        analyzer = FunctionAnalyzer(o["object_name"])
    else:
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
    return finder.superclass_names


def check_module_imports(o):
    with open(o["abs_file_path"], 'r', encoding='utf-8') as file:
        file_content = file.read()

    tree = ast.parse(file_content)
    collector = ImportCollector()
    collector.visit(tree)

    module_imports = []
    if collector.imported_modules is not None:
        for imp in collector.imported_modules:
            if imp is not None and "." in imp:
                met = generate_metadata(imp)
                if met is not None and met["object_type"] == "Module":
                    module_imports.append(met)

    return collector.imported_modules, module_imports


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

        object_type = "Unknown"

        module = importlib.import_module(module_path)

        if module.__name__ == obj_name:
            object_type = "Module"
        else:
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

        metadata["object_name"] = obj_name
        metadata["object_type"] = object_type
        potential_module_path = str(module.__file__).replace("__init__.py", f"{obj_name}.py")
        if module.__file__.endswith("__init__.py") and os.path.exists(potential_module_path):
            metadata["abs_file_path"] = potential_module_path
        else:
            metadata["abs_file_path"] = str(module.__file__)
        metadata["module_name"] = str(module.__name__)
        metadata["module_identifier"] = f"{str(module.__name__)}.{obj_name}"
        return metadata

    except (ModuleNotFoundError, AttributeError) as e:
        print(f"Error : {e}", package_path)
        return None


def generate_data_for_graph(root_namespaces):
    def extract_namespaces(target):
        if "." in target:
            parts = target.split('.')
            namespaces = []
            for index in range(len(parts) - 1):
                __namespace = '.'.join(parts[:index + 1])
                namespaces.append(__namespace)
            return namespaces
        else:
            return [target]

    def create_node(_nodes, nid, name, category_id):
        _nodes.append({
            "id": nid,
            "name": name,
            "label": {
                "normal": {
                    "show": True
                }
            },
            "category": category_id
        })

    nodes, links, categories = [], [], []
    _namespaces = set()

    # first derive the namespaces from the given set.
    for p in root_namespaces:
        x = extract_namespaces(p)
        for xi in x:
            if is_valid_namespace(xi):
                _namespaces.add(xi)

    targets = {}

    # then we iterate through each of the
    # target class/function/namespace.
    for p in root_namespaces:
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

    return nodes, links, categories, targets


def gen_graph(json_data):
    nodes = json_data["nodes"]
    links = json_data["links"]
    categories = json_data["categories"]

    from pyecharts import options as opts
    from pyecharts.charts import Graph

    return Graph(
        init_opts=opts.InitOpts(width="1000px", height="1000px", is_horizontal_center=True)) \
        .add(
        "",
        nodes=nodes,
        links=links,
        categories=categories,
        layout="circular",
        is_rotate_label=True,
        linestyle_opts=opts.LineStyleOpts(color="source", curve=0.3),
        label_opts=opts.LabelOpts(position="bottom", font_size=14),  # Increase the text size
    ) \
        .set_global_opts(
        title_opts=opts.TitleOpts(
            title="PyTorch Architecture Recovery",
            pos_top="30px",  # Add a top margin to the title
            title_textstyle_opts=opts.TextStyleOpts(font_size=24),  # Increase title font size
        ),
        legend_opts=opts.LegendOpts(
            pos_top="80px", orient="vertical", pos_left="2%"
        ),
    ) \
        .render_embed()


class AnalyzeSetBody(BaseModel):
    root_namespaces: List[str]


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("index.html", "r") as file:
        content = file.read()
    return HTMLResponse(content=content)


@app.post("/analyze_set")
async def analyze_set(data: AnalyzeSetBody):
    try:
        nodes, links, categories, targets = generate_data_for_graph(data.root_namespaces)
        html = gen_graph(to_json({
            "nodes": nodes,
            "links": links,
            "categories": categories
        }))
        # write_json_to_file(to_json({"nodes":nodes, "links":links, "categories":categories}), "data/viz.json")
        write_json_to_file(to_json(targets), "data/raw.json")
        return HTMLResponse(content=html)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
