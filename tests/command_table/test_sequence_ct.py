from zhinst.toolkit import Sequence, CommandTable


def test_setting_command_table(command_table_schema):
    sequencer = Sequence()
    ct = CommandTable(command_table_schema)
    sequencer.command_table = ct
    assert sequencer.command_table == ct


def test_setting_command_table_constructor(command_table_schema):
    ct = CommandTable(command_table_schema)
    sequencer = Sequence(command_table=ct)
    assert sequencer.command_table == ct
