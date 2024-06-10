import argparse
import os

import yaml


def get_config(argv=None):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        dest="config",
        required=False,
        type=str,
        default=os.environ.get("APP_CONFIG", "config.yaml"),
    )

    known, unknown = parser.parse_known_args()

    with open(known.config, encoding='utf-8') as f:
        return yaml.safe_load(f.read())["app"]
