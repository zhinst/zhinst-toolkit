import numpy as np
import pytest

from zhinst.toolkit.driver.modules.scope_module import ScopeModule


@pytest.fixture()
def scope_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_scope_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.scopeModule.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield ScopeModule(mock_connection.return_value.scopeModule(), session)


def test_repr(scope_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(scope_module)


def test_finish(scope_module, mock_connection):
    module_mock = mock_connection.return_value.scopeModule.return_value
    scope_module.finish()
    module_mock.finish.assert_called_with()


def test_progress(scope_module, mock_connection):
    module_mock = mock_connection.return_value.scopeModule.return_value
    module_mock.progress.return_value = 0.5 * np.ones(1)
    assert scope_module.progress() == 0.5


def test_read(scope_module, mock_connection):
    module_mock = mock_connection.return_value.scopeModule.return_value
    module_mock.read.return_value = {"/externalscaling": np.ones(1)}
    result = scope_module.read()
    assert scope_module.externalscaling in result
    assert result[scope_module.externalscaling][0] == 1
