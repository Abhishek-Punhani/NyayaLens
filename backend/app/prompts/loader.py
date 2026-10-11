import yaml
import jinja2
from pathlib import Path

_YAML_DIR = Path(__file__).parent / "yaml"


def render_prompt(yaml_name: str, context: dict) -> str:
    """Render a YAML prompt. Accepts 'name' or 'name.yaml'."""
    filename = yaml_name if yaml_name.endswith(".yaml") else f"{yaml_name}.yaml"
    yaml_path = _YAML_DIR / filename
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # StrictUndefined: a missing template variable must raise, not render blank.
    template = jinja2.Template(data["system_prompt"], undefined=jinja2.StrictUndefined)
    return template.render(**context)
