import builtins
import importlib
import json
import os
import sys


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


def is_valid_namespace(x) -> bool:
    return x is not None and x != "null" and \
        not is_builtin(x) \
        and not is_standard_library(x)


def write_json_to_file(json_obj, file_name):
    with open(file_name, 'w+') as f:
        json.dump(json_obj, f)
