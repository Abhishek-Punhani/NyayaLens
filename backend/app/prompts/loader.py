import yaml
import jinja2
from pathlib import Path

def render_prompt(yaml_name: str, context: dict) -> str:
    yaml_path = Path(__file__).parent / "yaml" / f"{yaml_name}.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    template = jinja2.Template(data["system_prompt"])
    return template.render(**context)
