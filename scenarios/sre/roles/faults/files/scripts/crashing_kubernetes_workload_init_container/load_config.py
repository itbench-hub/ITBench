import json
import sys

def main()
    try:
        with open('/etc/app-config/config.json', 'r') as f:
            data = json.load(f)

        items_count = len(data.get('configuration_items', []))

        print(f"Config loaded successfully with {items_count} configuration items")
        sys.exit(0)
    except json.JSONDecodeError as e:
        print(f"FATAL: Failed to parse configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: Unexpected error loading configuration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
