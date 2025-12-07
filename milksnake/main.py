from milksnake.agent import Agent
from milksnake.walkfile import parse_walkfile

def _read_walkfile():
    file = "walkfile.txt"
    with open(file, "r", encoding="utf-8") as f:
        entries = list(parse_walkfile(f))
    print(f"Loaded {len(entries)} entries from {file}")
    return entries

if __name__ == "__main__":
    entries = _read_walkfile()
    agent = Agent(entries)
    agent.run()