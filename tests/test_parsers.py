import numpy as np
import pytest

from zhinst.toolkit.driver.parsers import Parse


class TestParsers:
    def test_set_rf_lf(self):
        assert Parse.set_rf_lf("rf") == 1
        assert Parse.set_rf_lf("lf") == 0

    def test_get_rf_lf(self):
        assert Parse.get_rf_lf(1) == "rf"
        assert Parse.get_rf_lf(0) == "lf"

    def test_set_true_false(self):
        assert Parse.set_true_false(True) == 1
        assert Parse.set_true_false(False) == 0

    def test_get_true_false(self):
        assert Parse.get_true_false(1) == True
        assert Parse.get_true_false(0) == False

    def test_set_scope_mode(self):
        assert Parse.set_scope_mode("time") == 1
        assert Parse.set_scope_mode("FFT") == 3
        with pytest.raises(ValueError) as e_info:
            Parse.set_scope_mode("invalid")

    def test_get_scope_mode(self):
        assert Parse.get_scope_mode(1) == "time"
        assert Parse.get_scope_mode(3) == "FFT"
        with pytest.raises(ValueError) as e_info:
            Parse.get_scope_mode(2)

    def test_get_locked_status(self):
        assert Parse.get_locked_status(0) == "locked"
        assert Parse.get_locked_status(1) == "error"
        assert Parse.get_locked_status(2) == "busy"

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

    def test_deg2complex(self):
        assert Parse.deg2complex(complex(1, 1)) == complex(1, 1)
        assert Parse.deg2complex(20) == np.exp(1j * np.deg2rad(20))

    def test_complex2deg(self):
        assert Parse.complex2deg(np.exp(1j * np.deg2rad(20))) == 20
        assert Parse.complex2deg(complex(1, 1)) == 45.0

    def test_time2samples(self):
        assert Parse.uhfqa_time2samples(22) == 39600000000
        assert Parse.uhfqa_samples2time(39600000000) == 22
        assert Parse.shfqa_time2samples(22) == 33554428
        # TODO test why backwards path does not works?
        assert Parse.shfqa_samples2time(39600000000) == 19.8
