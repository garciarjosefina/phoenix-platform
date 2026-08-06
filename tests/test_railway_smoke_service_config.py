import re
import subprocess
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_RAILWAY_TOML = _REPO_ROOT / "railway.toml"
_RUNNER_MODULE_PATH = _REPO_ROOT / "platform" / "execution_gateway" / "bybit_demo_smoke_runner.py"

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _load():
    return tomllib.loads(_RAILWAY_TOML.read_text())


def _raw_text():
    return _RAILWAY_TOML.read_text()


# ---------------------------------------------------------------------------
# 1. Presencia y sintaxis
# ---------------------------------------------------------------------------

class TestFilePresence:
    def test_file_exists(self):
        assert _RAILWAY_TOML.is_file()

    def test_valid_toml_syntax(self):
        _load()  # no debe lanzar tomllib.TOMLDecodeError

    def test_top_level_sections_are_exactly_build_and_deploy(self):
        config = _load()
        assert set(config.keys()) == {"build", "deploy"}


# ---------------------------------------------------------------------------
# 2. Build command
# ---------------------------------------------------------------------------

class TestBuildCommand:
    def test_build_command_exact(self):
        config = _load()
        assert config["build"]["buildCommand"] == "python3 -m pip install ."

    def test_build_section_has_only_build_command(self):
        config = _load()
        assert set(config["build"].keys()) == {"buildCommand"}

    def test_build_command_installs_current_project(self):
        config = _load()
        assert config["build"]["buildCommand"].split()[-1] == "."

    def test_build_command_uses_module_invocation_not_bare_pip(self):
        # forma portable: python3 -m pip, no depende de que `pip` esté en PATH
        config = _load()
        assert config["build"]["buildCommand"].startswith("python3 -m pip install")

    def test_build_does_not_run_tests(self):
        config = _load()
        cmd = config["build"]["buildCommand"].lower()
        assert "pytest" not in cmd
        assert "test" not in cmd

    def test_build_does_not_install_dev_extras(self):
        config = _load()
        cmd = config["build"]["buildCommand"]
        assert "[dev]" not in cmd
        assert "-e " not in cmd
        assert "--editable" not in cmd

    def test_build_command_has_no_shell_chaining(self):
        config = _load()
        cmd = config["build"]["buildCommand"]
        for token in ("&&", "||", ";", "|", "$("):
            assert token not in cmd


# ---------------------------------------------------------------------------
# 3. Start command
# ---------------------------------------------------------------------------

class TestStartCommand:
    def test_start_command_exact(self):
        config = _load()
        assert config["deploy"]["startCommand"] == "python3 -m execution_gateway.bybit_demo_smoke_runner"

    def test_start_command_not_python_dash_c(self):
        config = _load()
        cmd = config["deploy"]["startCommand"]
        assert "-c" not in cmd.split()
        assert not cmd.startswith("python3 -c")
        assert not cmd.startswith("python -c")

    def test_start_command_uses_module_flag(self):
        config = _load()
        assert " -m " in config["deploy"]["startCommand"]

    def test_start_command_targets_the_accepted_runner_module(self):
        config = _load()
        assert config["deploy"]["startCommand"].endswith(
            "execution_gateway.bybit_demo_smoke_runner"
        )

    def test_start_command_no_web_server(self):
        config = _load()
        cmd = config["deploy"]["startCommand"].lower()
        for w in ("uvicorn", "gunicorn", "fastapi", "flask", "wsgi", "asgi", "--bind", "--port", "--host"):
            assert w not in cmd

    def test_start_command_no_shell_chaining_or_redirection(self):
        config = _load()
        cmd = config["deploy"]["startCommand"]
        for token in ("&&", "||", ";", "|", ">", "<", "$("):
            assert token not in cmd

    def test_start_command_no_retry_or_loop_or_sleep(self):
        config = _load()
        cmd = config["deploy"]["startCommand"].lower()
        for w in ("retry", "while", "for ", "sleep", "loop", "backoff"):
            assert w not in cmd

    def test_start_command_no_bash_wrapper(self):
        config = _load()
        cmd = config["deploy"]["startCommand"]
        assert not cmd.startswith("bash")
        assert not cmd.startswith("sh ")
        assert "bash -c" not in cmd


# ---------------------------------------------------------------------------
# 3b. Restart policy — el runner es one-shot; Railway no debe reintentarlo
# ---------------------------------------------------------------------------

class TestRestartPolicy:
    def test_restart_policy_type_is_present(self):
        config = _load()
        assert "restartPolicyType" in config["deploy"]

    def test_restart_policy_type_is_exactly_never(self):
        config = _load()
        assert config["deploy"]["restartPolicyType"] == "NEVER"

    def test_restart_policy_type_is_not_on_failure(self):
        config = _load()
        assert config["deploy"]["restartPolicyType"] != "ON_FAILURE"

    def test_restart_policy_type_is_not_always(self):
        config = _load()
        assert config["deploy"]["restartPolicyType"] != "ALWAYS"

    def test_restart_policy_type_casing_is_exact(self):
        config = _load()
        value = config["deploy"]["restartPolicyType"]
        assert value == value.upper()
        assert value != "never"
        assert value != "Never"

    def test_no_restart_policy_max_retries(self):
        config = _load()
        assert "restartPolicyMaxRetries" not in config["deploy"]

    def test_no_second_or_contradictory_restart_policy(self):
        # una sola clave de política de reinicio, un solo valor, sin
        # duplicados dentro de [deploy] (tomllib ya rechazaría una clave
        # TOML duplicada, pero esto además fija que no exista una variante
        # de nombre alternativa apuntando a otra política).
        config = _load()
        deploy = config["deploy"]
        restart_keys = [k for k in deploy if "restart" in k.lower()]
        assert restart_keys == ["restartPolicyType"]

    def test_deploy_section_has_only_start_command_and_restart_policy(self):
        config = _load()
        assert set(config["deploy"].keys()) == {
            "startCommand", "restartPolicyType",
        }

    def test_full_config_has_only_the_expected_shape(self):
        config = _load()
        assert config == {
            "build": {"buildCommand": "python3 -m pip install ."},
            "deploy": {
                "startCommand": "python3 -m execution_gateway.bybit_demo_smoke_runner",
                "restartPolicyType": "NEVER",
            },
        }


# ---------------------------------------------------------------------------
# 4. Seguridad y alcance
# ---------------------------------------------------------------------------

class TestSecurityAndScope:
    def test_no_phoenix_variables(self):
        text = _raw_text()
        assert "PHOENIX_" not in text

    def test_no_secret_like_tokens(self):
        text = _raw_text().upper()
        for forbidden in ("API_KEY", "APIKEY", "SECRET", "TOKEN", "PASSWORD"):
            assert forbidden not in text

    def test_no_mainnet_or_testnet(self):
        text = _raw_text().lower()
        assert "mainnet" not in text
        assert "testnet" not in text

    def test_no_bybit_urls(self):
        text = _raw_text().lower()
        assert "bybit.com" not in text

    def test_no_domain_configuration(self):
        text = _raw_text().lower()
        assert "domain" not in text

    def test_no_cron_or_schedule(self):
        text = _raw_text().lower()
        assert "cron" not in text
        assert "schedule" not in text

    def test_no_healthcheck(self):
        config = _load()
        deploy = config.get("deploy", {})
        assert "healthcheckPath" not in deploy
        assert "healthcheckTimeout" not in deploy

    def test_no_replicas(self):
        config = _load()
        assert "numReplicas" not in config.get("deploy", {})

    def test_no_railway_project_or_service_ids(self):
        text = _raw_text()
        assert _UUID_RE.search(text) is None

    def test_no_github_credentials(self):
        text = _raw_text().lower()
        for forbidden in ("ghp_", "github_pat_", "ssh-rsa"):
            assert forbidden not in text

    def test_no_env_file_reference(self):
        text = _raw_text().lower()
        assert ".env" not in text

    def test_no_environment_printing_commands(self):
        text = _raw_text().lower()
        assert "printenv" not in text
        assert re.search(r"\benv\b", text) is None
        assert "export " not in text

    def test_no_shell_scripts_inline(self):
        text = _raw_text()
        assert "#!/" not in text


# ---------------------------------------------------------------------------
# 5. El módulo del Start Command existe y es importable
# ---------------------------------------------------------------------------

class TestStartCommandModuleExists:
    def test_runner_module_file_exists(self):
        assert _RUNNER_MODULE_PATH.is_file()

    def test_runner_module_importable_with_project_pythonpath(self):
        import execution_gateway.bybit_demo_smoke_runner as runner
        assert hasattr(runner, "main")

    def test_start_command_module_path_matches_real_file_location(self):
        config = _load()
        module_dotted = config["deploy"]["startCommand"].rsplit(" -m ", 1)[1]
        module_relative_path = module_dotted.replace(".", "/") + ".py"
        assert (_REPO_ROOT / "platform" / module_relative_path).is_file()


# ---------------------------------------------------------------------------
# 6. Instalación real en entorno limpio (venv temporal)
# ---------------------------------------------------------------------------

class TestCleanInstallation:
    def test_pip_install_dot_produces_importable_top_level_package(self, tmp_path):
        venv_dir = tmp_path / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True, capture_output=True, timeout=60,
        )
        venv_python = venv_dir / "bin" / "python3"

        install = subprocess.run(
            [str(venv_python), "-m", "pip", "install", str(_REPO_ROOT)],
            capture_output=True, text=True, timeout=120,
        )
        assert install.returncode == 0, install.stderr

        check = subprocess.run(
            [str(venv_python), "-c", "import execution_gateway; print(execution_gateway.__file__)"],
            capture_output=True, text=True, timeout=20,
        )
        assert check.returncode == 0, check.stderr
        assert "site-packages" in check.stdout

    def test_installed_package_does_not_require_pythonpath(self, tmp_path):
        venv_dir = tmp_path / "venv"
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True, capture_output=True, timeout=60,
        )
        venv_python = venv_dir / "bin" / "python3"
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", str(_REPO_ROOT)],
            check=True, capture_output=True, timeout=120,
        )

        result = subprocess.run(
            [str(venv_python), "-m", "execution_gateway.bybit_demo_smoke_runner"],
            capture_output=True, text=True, timeout=15,
            cwd=str(tmp_path),
            env={"PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 1
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE" in result.stdout
        assert result.stderr == ""


# ---------------------------------------------------------------------------
# 7. Ejecución controlada del runner (sin instalación, vía PYTHONPATH de pytest)
# ---------------------------------------------------------------------------

class TestControlledExecution:
    def test_runner_fails_safely_without_credentials(self):
        env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(_REPO_ROOT / "platform")}
        result = subprocess.run(
            [sys.executable, "-m", "execution_gateway.bybit_demo_smoke_runner"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT), env=env, timeout=10,
        )
        assert result.returncode == 1
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE" in result.stdout
        assert result.stderr == ""
        assert "Traceback" not in result.stdout
        assert result.stdout.count("PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE") == 1

    def test_runner_succeeds_with_network_substituted_no_real_connection(self):
        program = (
            "import json, urllib.request\n"
            "class FR:\n"
            "    def read(self):\n"
            "        return json.dumps({'retCode': 0, 'retMsg': 'OK', 'result': {},"
            " 'retExtInfo': {}, 'time': 1700000000000}).encode()\n"
            "    def __enter__(self):\n"
            "        return self\n"
            "    def __exit__(self, *a):\n"
            "        return False\n"
            "urllib.request.urlopen = lambda *a, **k: FR()\n"
            "import runpy\n"
            "runpy.run_module('execution_gateway.bybit_demo_smoke_runner', run_name='__main__')\n"
        )
        env = {
            "PATH": "/usr/bin:/bin", "PYTHONPATH": str(_REPO_ROOT / "platform"),
            "PHOENIX_BYBIT_DEMO_API_KEY": "demo-key",
            "PHOENIX_BYBIT_DEMO_API_SECRET": "demo-secret",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
            "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
        }
        result = subprocess.run(
            [sys.executable, "-c", program],
            capture_output=True, text=True, cwd=str(_REPO_ROOT), env=env, timeout=10,
        )
        assert result.returncode == 0
        assert "PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS" in result.stdout
        assert result.stderr == ""
