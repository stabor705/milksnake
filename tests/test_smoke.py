def test_imports():
    # Import the package and key modules without executing runtime code
    import milksnake
    from milksnake.agent import Agent

    assert hasattr(Agent, "run")
