import phoenix_core


def test_import():
    assert phoenix_core is not None


def test_version():
    assert phoenix_core.__version__ == "0.1.0"
