import pytest
import asyncio

# Use a single event loop for all async tests
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()
