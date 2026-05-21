from ops_cli.commands.run import frontend_dev_command, frontend_dev_env


def test_frontend_dev_command_does_not_add_separator_for_pnpm() -> None:
    assert frontend_dev_command("pnpm.cmd", 9001) == [
        "pnpm.cmd",
        "run",
        "dev",
        "--port",
        "9001",
    ]


def test_frontend_dev_command_adds_separator_for_npm() -> None:
    assert frontend_dev_command("npm.cmd", 9001) == [
        "npm.cmd",
        "run",
        "dev",
        "--",
        "--port",
        "9001",
    ]


def test_frontend_dev_env_overrides_proxy_to_backend_port() -> None:
    env = frontend_dev_env({"EXISTING": "1"}, backend_port=9000, frontend_port=9001)

    assert env["EXISTING"] == "1"
    assert env["VITE_API_BASE_URL"] == "http://127.0.0.1:9000/api"
    assert env["VITE_PORT"] == "9001"
    assert env["PORT"] == "9001"
    assert env["VITE_PROXY"] == '[["/api","http://127.0.0.1:9000/api"]]'
