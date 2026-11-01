import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json
from src.config import Settings
from src.storage import Store

parser = argparse.ArgumentParser(description="Change a synthetic service fixture for the replanning demo.")
parser.add_argument("service", choices=["wifi", "vpn", "printing", "accounts"])
parser.add_argument("status", choices=["operational", "degraded", "outage"])
parser.add_argument("--detail", default="Synthetic scenario change; recovery time unknown.")
args = parser.parse_args()
store = Store(Settings().data_dir)
store.set_service(args.service, args.status, args.detail)
print(json.dumps(store.service(args.service), indent=2))
