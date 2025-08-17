import os
import re
import requests
import json
from distutils.version import LooseVersion
from jinja2 import Environment, FileSystemLoader


BASE_URL = "https://ascend-repo.obs.cn-east-2.myhuaweicloud.com"
ALPHA_DICT = {
    "8.0.RC2.alpha001": "V100R001C18B800TP015",
    "8.0.RC2.alpha002": "V100R001C18SPC805",
    "8.0.RC2.alpha003": "V100R001C18SPC703",
    "8.0.RC3.alpha002": "V100R001C19SPC702",
    "8.1.RC1.alpha001": "V100R001C21B800TP034",
    "8.1.RC1.alpha002": "V100R001C21B800TP051",
    "8.2.RC1.alpha004": "V100R001C22B800TP054",
}

env = Environment(loader=FileSystemLoader('tools/template'))

def get_python_download_url(version): 
    try:
        response = requests.get("https://www.python.org/ftp/python/")
        response.raise_for_status()
        versions = re.findall(rf"{version}\.[0-9]+", response.text)
        if not versions:
            print(f"[WARNING] Could not find the latest version for Python {version}")
            exit(1)
        py_latest_version = sorted(versions, key=LooseVersion)[-1]
        print(f"Latest Python version found: {py_latest_version}")
    
    except requests.RequestException as e:
        print(f"[WARNING] Error fetching Python versions: {e}")
        exit(1)
        
    py_installer_package = "Python-" + py_latest_version
    py_installer_url = os.path.join("https://repo.huaweicloud.com/python/", py_latest_version, py_installer_package + ".tgz")
    return py_installer_package, py_installer_url, py_latest_version

def get_cann_download_url(cann_chip, version):
    if "alpha" in version:
        if version not in ALPHA_DICT:
            raise ValueError(f"Unsupported version: {version}. Supported versions are: {list(ALPHA_DICT.keys())}")
        url_prefix = f"{BASE_URL}/Milan-ASL/Milan-ASL%20{ALPHA_DICT[version]}"
    else:
        url_prefix = f"{BASE_URL}/CANN/CANN%20{version}"
    
    toolkit_file_prefix = "Ascend-cann-toolkit_" + version + "_linux"
    nnal_file_prefix = "Ascend-cann-nnal_" + version + "_linux"
    
    if cann_chip == "Atlas-A3":
        kernels_file_prefix = cann_chip + "-cann-kernels" + "_" + version + "_linux"
    else:
        kernels_file_prefix = "Ascend-cann-kernels-" + cann_chip + "_" + version + "_linux"
    
    cann_toolkit_url_prefix = f"{url_prefix}/{toolkit_file_prefix}"
    cann_kernels_url_prefix = f"{url_prefix}/{kernels_file_prefix}"   
    cann_nnal_url_prefix = f"{url_prefix}/{nnal_file_prefix}"
    
    return cann_toolkit_url_prefix, cann_kernels_url_prefix, cann_nnal_url_prefix

def prepare_common_item_data(item, template):
    py_installer_package, py_installer_url, py_latest_version = get_python_download_url(item["py_version"])
    item["py_installer_package"] = py_installer_package
    item["py_installer_url"] = py_installer_url
    item["py_latest_version"] = py_latest_version
    
    cann_toolkit_url_prefix, cann_kernels_url_prefix, cann_nnal_url_prefix = get_cann_download_url(
        item["cann_chip"], 
        item["cann_version"],
    )
    item["cann_toolkit_url_prefix"] = cann_toolkit_url_prefix
    item["cann_kernels_url_prefix"] = cann_kernels_url_prefix
    item["cann_nnal_url_prefix"] = cann_nnal_url_prefix
    
    rendered_content = template.render(item=item)
    
    if item["cann_chip"] == "Atlas-A3":
        cann_chip_type = "a3"
    else:
        cann_chip_type = item["cann_chip"]
    
    return rendered_content, cann_chip_type
            
def render_and_save_cann_dockerfile(args, ubuntu_template, openeuler_template):
    if "cann" not in args or not args["cann"]:
        return
    
    for item in args["cann"]:
        if item["os_name"] == "ubuntu":
            template_name = ubuntu_template
        else:
            template_name = openeuler_template
            
        template = env.get_template(template_name)
        rendered_content, cann_chip_type = prepare_common_item_data(item, template)
        output_path = os.path.join(
            "cann",
            f"{item['cann_version'].lower()}-{cann_chip_type}-{item['os_name']}{item['os_version']}-py{item['py_version']}",
            "Dockerfile"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(rendered_content)
        
def render_and_save_manylinux_dockerfile(args, manylinux_template):
    if "manylinux" not in args or not args["manylinux"]:
        return
        
    for item in args["manylinux"]:
        template = env.get_template(manylinux_template)
        
        rendered_content, cann_chip_type = prepare_common_item_data(item, template)

        output_path = os.path.join(
            "manylinux",
            f"{item['cann_version'].lower()}-{cann_chip_type}-{item['os_name']}_{item['os_version']}-py{item['py_version']}",
            "Dockerfile"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(rendered_content)   
        
def main():  
    with open('build_manylinux_arg.json', 'r') as fm:
        args = json.load(fm)
    render_and_save_manylinux_dockerfile(args, "manylinux.Dockerfile.j2")
    

if __name__ == "__main__":
    main()

