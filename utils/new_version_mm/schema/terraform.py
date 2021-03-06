import os
import pystache
import re

from common.utils import (find_property, process_override_codes,
                          underscore, write_file)
from common.preprocess import find_parameter


def build_terraform_yaml(info, output):
    data = []
    for v in info:
        config = v.get("custom_configs").get("terraform")
        if not config:
            continue

        r = {}
        examples = config.get("examples")
        if examples:
            r.update(_generate_example_config(examples, v))

        c = config.get("overrides")
        if c:
            _generate_override(
                c, v["api_info"], v["properties"],
                v["resource_name"], r)

        if r:
            r["name"] = v["resource_name"]
            data.append(r)

    s = pystache.Renderer().render_path("template/terraform.mustache",
                                        {"resources": data})

    write_file(output + "terraform.yaml", [s])


def _generate_override(overrides, api_info, properties,
                       resource_name, result):

    property_overrides = {}
    api_parameter_overrides = {}
    api_async_overrides = {}

    for path, v in overrides.items():
        if "to_request" in v or "to_request_method" in v:
            api_parameter_overrides[path] = v

        elif "from_response" in v or "from_response_method" in v:
            property_overrides[path] = v

        elif "async_status_check_func" in v:
            api_async_overrides[path] = v

        else:
            raise Exception("find unspported override item(%s) for "
                            "resource(%s)" % (
                                " ".join(v.keys()), resource_name))

    if property_overrides:
        result.update(
            _generate_property_override(property_overrides, properties))

    if api_parameter_overrides:
        result.update(
            _generate_api_parameter_override(
                api_parameter_overrides, api_info))

    if api_async_overrides:
        result.update(
            _generate_api_async_override(api_async_overrides, api_info))


def _generate_property_override(overrides, properties):
    pros = []
    for path, v in overrides.items():

        find_property(properties, path)

        m = {"prop_path": path}

        if "from_response" in v:
            m["from_response"] = process_override_codes(
                v.get("from_response"), 10)

        elif "from_response_method" in v:
            m["from_response_method"] = v.get("from_response_method")

        pros.append(m)

    return {
        "properties": pros,
        "has_property_override": True
    }


def _generate_api_parameter_override(overrides, api_info):
    params = []
    for path, v in overrides.items():
        pv = path.split(".")

        api = api_info.get(underscore(pv[0]))
        if not api:
            raise Exception("unknown api index(%s)" % pv[0])

        path = ".".join(pv[1:])
        if api.get("msg_prefix"):
            path = path.replace(api.get("msg_prefix") + ".", "", 1)

        find_parameter(path, api["body"], api["all_models"])

        m = {"prop_path": "%s.%s" % (api["api_index"], path)}

        if "to_request" in v:
            m["to_request"] = process_override_codes(v.get("to_request"), 10)

        elif "to_request_method" in v:
            m["to_request_method"] = v.get("to_request_method")

        params.append(m)

    return {
        "parameters": params,
        "has_parameter_override": True
    }


def _generate_api_async_override(overrides, api_info):
    pros = []
    for path, v in overrides.items():
        path1 = underscore(path)
        if path1 not in api_info:
            raise Exception("unknown api index(%s)" % path)

        pros.append({
            "api": path1,
            "custom_status_check_func": v.get("async_status_check_func")
        })

    return {
        "api_asyncs": pros,
        "has_async_override": True
    }


def _generate_example_config(examples, info):
    trn = underscore("%s_%s_%s_%s" % (
        info["cloud_full_name"], info["service_type"],
        info["resource_name"], info["version"]))

    m = re.compile(r"resource \"%s\" \"(.*)\" {" % trn)

    def _find_id(f):
        tf = None
        with open(f, "r") as o:
            tf = o.readlines()

        r = []
        for i in tf:
            v = m.match(i)
            if v:
                r.append(v)

        if len(r) != 1:
            raise Exception("Find zero or one more terraform resource(%s) "
                            "in tf file(%s), or the format is not "
                            "correct" % (trn, f))

        return r[0].group(1)

    result = [
        {
            "name": os.path.basename(f["path"]).split(".")[0],
            "resource_id": _find_id(info["config_dir"] + f["path"]),
            "description": f["description"]
        }
        for f in examples
    ]
    if result:
        result[0]["is_basic"] = True

    return {"examples": result, "has_example": len(result) > 0}
