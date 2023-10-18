"""Custom sequence code class."""
from zhinst.toolkit.waveform import Waveforms
from zhinst.toolkit.command_table import CommandTable
import re
import typing as t


class Sequence:
    r"""A representation of a ZI sequencer code.

    This class enables a compact representation of a sequence for a Zurich
    Instruments device. Although a sequencer code can be represented by a
    simple string this class offers the following advantages:

        * Define a constants dictionary. The constants will be added
          automatically to the top of the resulting sequencer code and helps
          to prevent the use of fstrings (which require the escaping of {})
        * Link Waveforms to the sequence. This adds the waveform placeholder
          definitions to the top of the resulting sequencer code.

    Note:
        This class is only for convenience. The same functionality can be
        achieved with a simple string.

    Args:
        code: Sequencer code (default = None).
        constants: A dictionary of constants to be added to the top of the
            resulting sequencer code. (default = None).
        waveforms: Waveforms that will be used in the sequence.

    Example:
        >>> waveforms = Waveforms()
        >>> waveforms[0] = (0.5*np.ones(1008), -0.2*np.ones(1008), np.ones(1008))
        >>> sequencer = Sequence()
        >>> sequencer.constants["PULSE_WIDTH"] = 10e-9 #ns
        >>> sequencer.waveforms = waveforms
        >>> sequencer.code = \"\"\"\
            // Hello World
            repeat(5)
            ...
            \"\"\"
        >>> str(sequencer)
            // Constants
            const PULSE_WIDTH = 10e-9;
            // Waveforms declaration
            assignWaveIndex(placeholder(1008, true, false), placeholder(1008, \
                false, false), 0);
            assignWaveIndex(placeholder(1008, false, false), placeholder(1008, \
                false, false), 2);
            // Hello World
            repeat(5)
            ...
    """

    def __init__(
        self,
        code: str = None,
        *,
        constants: t.Dict[str, float] = None,
        waveforms: Waveforms = None,
        command_table: CommandTable = None,
    ):
        self._partial_seq = code if code else ""
        self._constants = constants if constants else {}
        self._waveforms = waveforms
        self._command_table = command_table

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self, *, waveform_snippet: bool = True) -> str:
        """Convert the object into a string.

        Args:
            waveform_snippet: Flag if the waveform declaration should be added
                to the top of the resulting sequence. (default = True).

        Returns:
            String representation of the sequence.
        """
        sequence = self._partial_seq
        if waveform_snippet and self._waveforms:
            sequence = (
                "// Waveforms declaration\n"
                + self._waveforms.get_sequence_snippet()
                + "\n"
                + sequence
            )
        new_constants = {}
        for key, value in self._constants.items():
            constant_regex = re.compile(rf"(const {key} *= *)(.*);")
            if constant_regex.search(sequence):
                sequence = constant_regex.sub(rf"\g<1>{value};", sequence)
            else:
                new_constants[key] = value
        if len(new_constants) > 0:
            sequence = (
                "// Constants\n"
                + "\n".join(
                    [f"const {key} = {value};" for key, value in new_constants.items()]
                )
                + "\n"
                + sequence
            )
        return sequence

    @property
    def code(self) -> str:
        """Code of the Sequence."""
        return self._partial_seq

    @code.setter
    def code(self, value: str) -> None:
        """Code of the Sequence."""
        self._partial_seq = value

    @property
    def constants(self) -> t.Dict[str, float]:
        """Constants of the Sequence."""
        return self._constants

    @constants.setter
    def constants(self, value: t.Dict[str, float]) -> None:
        """Constants of the Sequence."""
        self._constants = value

    @property
    def waveforms(self) -> Waveforms:
        """Waveforms of the Sequence."""
        return self._waveforms

    @waveforms.setter
    def waveforms(self, value: Waveforms) -> None:
        """Waveforms of the Sequence."""
        self._waveforms = value

    @property
    def command_table(self) -> CommandTable:
        """Command table of the Sequence."""
        return self._command_table

    @command_table.setter
    def command_table(self, value: CommandTable) -> None:
        """Command table of the Sequence."""
        self._command_table = value
