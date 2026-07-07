from app.tasks.sample import hello


def test_hello_task() -> None:
    result = hello.run(name="world")
    assert result == "Hello, world!"
