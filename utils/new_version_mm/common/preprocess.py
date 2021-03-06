import re


def find_struct(datatype, all_models):
    if datatype in [
            'int', 'long', 'float', 'str', 'bool', 'date', 'datetime']:
        raise Exception("Can't find struct of datatype(%s)" % datatype)

    if datatype in all_models:
        return all_models[datatype]

    if datatype.startswith('list['):
        sub_datatype = re.match(r"list\[(.*)\]", datatype).group(1)
        return find_struct(sub_datatype, all_models)

    if datatype.startswith('dict('):
        sub_datatype = re.match(r"dict\(([^,]*), (.*)\)", datatype).group(2)
        return find_struct(sub_datatype, all_models)

    raise Exception("Can't find struct of datatype(%s) "
                    "in all models" % datatype)


def find_parameter(name, struct, all_models, delimiter="."):
    ns = name
    if isinstance(name, str):
        ns = name.split(delimiter)

    if not ns:
        raise Exception("Can't find the parameter with no name")

    n = ns[0]

    if not isinstance(struct, list):
        raise Exception("Can't find the parameter(%s) in a Non-Struct "
                        "model" % n)

    p = None
    index = 0
    for i, v in enumerate(struct):
        if v["name"] == n:
            p = v
            index = i
            break
    else:
        raise Exception("Can't find the parameter(%s) in struct" % n)

    if len(ns) == 1:
        return index, struct

    return find_parameter(
        ns[1:],
        find_struct(p["datatype"], all_models),
        all_models, delimiter)


def _change_type(index, parent, new_type):
    parent[index]["datatype"] = new_type


def _set_alias(index, parent, alias):
    parent[index]["alias"] = alias


def _change_required(index, parent, value):
    parent[index]["mandatory"] = value in ["true", "yes", 1]


def preprocess(struct, all_models, cmds):
    m = {
        "delete": lambda i, p: p.pop(i),
        "change_type": _change_type,
        # support change_required at adjust stage
        # "change_required": _change_required,

        # set_value, depends_on, allow_empty: only check the index of parameter
        # it will be executed on schema stage, otherwise its value will be
        # lost, because the merge function doesn't care about them.
        "set_value": lambda i, p, v: i,
        "set_array_num": lambda i, p, v: i,
        "depends_on": lambda i, p, o: find_parameter(o, struct, all_models),
        "allow_empty": lambda i, p: i,
        "set_alias": _set_alias
    }

    for i in cmds:
        cmd = re.sub(r" +", " ", i).split(" ")

        f = m.get(cmd[0])
        if not f:
            raise Exception("Unknown pre-process cmd(%s)" % cmd[0])

        delimiter = "."
        if cmd[1] in ["-F", "-f"]:
            delimiter = cmd[2]
            cmd = cmd[2:]

        index, parent = find_parameter(cmd[1], struct, all_models, delimiter)
        f(index, parent, *cmd[2:])
