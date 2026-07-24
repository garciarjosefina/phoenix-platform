import execution_gateway


def test_import():
    assert execution_gateway is not None


def test_version():
    assert execution_gateway.__version__ == "0.1.0"
