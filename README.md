# Milksnake - a SNMP simulator

Milksnake will be a program capable of simulating SNMP devices based on provided MIB files. Once run,
it will listen for SNMP request and respond in configured way.

## Running
```bash
uv sync
uv run python -m milksnake.main
```

## Testing
```bash
uv sync --dev
uv run pytest
```