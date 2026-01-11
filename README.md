# Milksnake - a SNMP simulator

Milksnake will be a program capable of simulating SNMP devices based on provided MIB files. Once run,
it will listen for SNMP request and respond in configured way.

## Running
```bash
uv sync
uv run python -m milksnake.main [OPTIONS]
```

Available options:

- `-c, --config PATH` - Path to YAML configuration file
- `-p, --port PORT` - UDP port to listen on (default: 9161)
- `--read-community STRING` - Read community string for SNMP GET requests (default: public)
- `--write-community STRING` - Write community string for SNMP SET requests (default: private)
- `--trap-community STRING` - Community string for SNMP traps (default: public)
- `-w, --walkfile PATH` - Path to walkfile containing OID definitions (default: walkfile.txt)


## Testing
```bash
uv sync --dev
uv run pytest
```

## Configuration File

Create a `config.yaml` file:

```yaml
port: 9161
read_community: "public"
write_community: "private"
trap_community: "public"
walkfile: "walkfile.txt"
```

Then run with:

```bash
uv run python -m milksnake.main --config config.yaml
```

# TODO
- Add makefile/justfile
- Make sure the names are good quality
- Add pre-commit hook for format checking?
