def test_imports():
    from milksnake.agent import Agent

    assert hasattr(Agent, "run")
