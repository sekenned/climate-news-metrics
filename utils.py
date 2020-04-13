import json
import yaml
from pathlib import Path 

def read_config(config_file: str = ".config.yaml") -> dict:
    """
    input file path to secrets.yaml file
    parse the file
    output the resulting dictionary 
    """
    with open(config_file, "r") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)


def initialize_json_directory(directory: str) -> Path:
    p = Path(directory)
    if not p.exists():
        p.mkdir()
    return p


def save_doc_json_to_file(doc: dict, directory: Path):
    filename = f"{Path(doc['_id']).parts[-1]}.json"
    full_path = directory.joinpath(filename)
    with open(full_path, 'w') as f: 
        f.write(json.dumps(doc))


# def secrets(secrets_file: str = ".secret.yaml") -> dict:
#     """
#     input file path to secrets.yaml file
#     parse the file
#     output the resulting dictionary 
#     """
#     with open(secrets_file, "r") as f:
#         try:
#             return yaml.safe_load(f)
#         except yaml.YAMLError as e:
#             print(e)