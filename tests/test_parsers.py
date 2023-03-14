import pytest

from zhinst.toolkit.driver.parsers import Parse


class TestParsers:
    def test_set_true_false(self):
        assert Parse.from_bool(True) == 1
        assert Parse.from_bool(False) == 0

    def test_get_true_false(self):
        assert Parse.to_bool(1) == True
        assert Parse.to_bool(0) == False

    def test_phase(self):
        assert Parse.phase(90) == 90
        assert Parse.phase(450) == 90
        assert Parse.phase(870) == 150

    def test_greater_equal(self, caplog):
        assert Parse.greater_equal(90, 0) == 90
        assert Parse.greater_equal(0, 0) == 0
        assert Parse.greater_equal(-20, 10) == 10
        assert len(caplog.records) == 1
        assert Parse.greater_equal(9.999999999999, 10) == 10
        assert len(caplog.records) == 2

    def test_smaller_equal(self, caplog):
        assert Parse.smaller_equal(-90, 0) == -90
        assert Parse.smaller_equal(0, 0) == 0
        assert Parse.smaller_equal(20, 10) == 10
        assert len(caplog.records) == 1
        assert Parse.smaller_equal(200000000000, 10) == 10
        assert len(caplog.records) == 2

    def test_multiple_of(self, caplog):
        assert Parse.multiple_of(10, 6, "nearest") == 12
        assert len(caplog.records) == 1
        assert Parse.multiple_of(10, 6, "down") == 6
        assert len(caplog.records) == 2
        assert Parse.multiple_of(12, 6, "down") == 12
        assert len(caplog.records) == 2
        with pytest.raises(ValueError):
            Parse.multiple_of(100, 6, "up")
