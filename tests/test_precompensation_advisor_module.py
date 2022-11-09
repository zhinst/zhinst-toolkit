import pytest


from zhinst.toolkit.driver.modules.precompensation_advisor_module import (
    PrecompensationAdvisorModule,
)


@pytest.fixture()
def precomensation_advisor_module(data_dir, mock_connection, session):
    json_path = data_dir / "nodedoc_precomensation_advisor_test.json"
    with json_path.open("r", encoding="UTF-8") as file:
        nodes_json = file.read()
    mock_connection.return_value.precompensationAdvisor.return_value.listNodesJSON.return_value = (
        nodes_json
    )
    yield PrecompensationAdvisorModule(
        mock_connection.return_value.precompensationAdvisor(), session
    )


def test_repr(precomensation_advisor_module):
    assert "MagicMock(DataServerSession(localhost:8004))" in repr(
        precomensation_advisor_module
    )


def test_raw_module(precomensation_advisor_module, mock_connection):
    assert (
        precomensation_advisor_module.raw_module
        == mock_connection.return_value.precompensationAdvisor()
    )


def test_device(zi_devices_json, precomensation_advisor_module, mock_connection):
    connected_devices = "dev1234"

    def get_string_side_effect(arg):
        if arg == "/zi/devices":
            return zi_devices_json
        if arg == "/zi/devices/connected":
            return connected_devices
        if arg == "/dev1234/features/devtype":
            return "Test"
        raise RuntimeError("ZIAPINotFoundException")

    mock_connection.return_value.getString.side_effect = get_string_side_effect

    # get
    mock_connection.return_value.precompensationAdvisor.return_value.getString.return_value = (
        ""
    )
    result = precomensation_advisor_module.device()
    assert result == ""

    mock_connection.return_value.precompensationAdvisor.return_value.getString.return_value = (
        "dev1234"
    )
    result = precomensation_advisor_module.device()
    assert result.serial == "dev1234"

    # set
    precomensation_advisor_module.device("dev1634")
    mock_connection.return_value.precompensationAdvisor.return_value.set.assert_called_with(
        "/device", "dev1634"
    )

    precomensation_advisor_module.device(result)
    mock_connection.return_value.precompensationAdvisor.return_value.set.assert_called_with(
        "/device", "dev1234"
    )
