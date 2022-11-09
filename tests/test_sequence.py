import numpy as np

from zhinst.toolkit import Sequence, Waveforms


def test_assignment():
    seq1 = Sequence("Test", constants={"TEST": 1}, waveforms=Waveforms())

    assert seq1.code == "Test"
    seq1.code = "new value"
    assert seq1.code == "new value"

    assert seq1.constants["TEST"] == 1
    seq1.constants["TEST"] = 2
    assert seq1.constants["TEST"] == 2
    seq1.constants["VALUE"] = 100
    assert seq1.constants["VALUE"] == 100

    assert list(seq1.waveforms.keys()) == []
    waves = Waveforms()
    waves[0] = np.ones(100)
    waves[3] = np.ones(100)
    seq1.waveforms = waves
    assert list(seq1.waveforms.keys()) == [0, 3]


def test_to_string():
    waveforms = Waveforms()
    waveforms[0] = (0.5 * np.ones(1008), -0.2 * np.ones(1008), np.ones(1008))

    sequencer = Sequence()
    sequencer.constants["PULSE_WIDTH"] = 10e-9  # ns
    sequencer.waveforms = waveforms
    sequencer.code = """\
// Hello World
repeat(5)
..."""

    assert sequencer.to_string() == str(sequencer)
    assert (
        sequencer.to_string()
        == """\
// Constants
const PULSE_WIDTH = 1e-08;
// Waveforms declaration
assignWaveIndex(placeholder(1008, true, false), placeholder(1008, false, false), 0);
// Hello World
repeat(5)
..."""
    )

    sequencer.constants = {}
    assert (
        sequencer.to_string()
        == """\
// Waveforms declaration
assignWaveIndex(placeholder(1008, true, false), placeholder(1008, false, false), 0);
// Hello World
repeat(5)
..."""
    )

    assert (
        sequencer.to_string(waveform_snippet=False)
        == """\
// Hello World
repeat(5)
..."""
    )
    sequencer.waveforms = None
    assert (
        sequencer.to_string()
        == """\
// Hello World
repeat(5)
..."""
    )


def test_to_string_existing_constant():
    sequencer = Sequence()
    sequencer.constants["PULSE_WIDTH"] = 10e-9
    sequencer.constants["TEST"] = 10
    sequencer.code = """\
// Hello World
repeat(5)
{
    const PULSE_WIDTH = 5;

    PULSE_WIDTH
}
..."""

    assert (
        sequencer.to_string()
        == """\
// Constants
const TEST = 10;
// Hello World
repeat(5)
{
    const PULSE_WIDTH = 1e-08;

    PULSE_WIDTH
}
..."""
    )
