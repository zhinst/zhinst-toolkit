"""Dictionary like waveform representation."""
import json
import typing as t
import warnings
from collections.abc import MutableMapping
from enum import IntFlag
from io import BytesIO

import numpy as np
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from zhinst.utils import convert_awg_waveform, parse_awg_waveform

from zhinst.toolkit.exceptions import ValidationError

_Waveform = t.Tuple[np.ndarray, t.Optional[np.ndarray], t.Optional[np.ndarray]]


class OutputType(IntFlag):
    """Waveform output type.

    OUT1: Enables the output 1 for the respective wave.
    OUT2: Enables the output 2 for the respective wave.

    .. versionadded:: 0.3.5
    """

    OUT1 = 1
    OUT2 = 2


class Wave(np.ndarray):
    """Numpy array subclass containing additional waveform metadata.

    This class takes a standard ndarray that already exists, casts as Wave
    type, and adds the following extra attributes/metadata:
    * name
    * output

    The additional metadata is only used for the sequencer code generation.

    (Based on https://numpy.org/doc/stable/user/basics.subclassing.html)

    Args:
        input_array: existing ndarray
        name: optional name of the waveform in the sequencer code snippet.
        output: optional output configuration for the waveform in the
                sequencer code snippet.

    .. versionadded:: 0.3.5
    """

    def __new__(
        cls,
        input_array,
        name: t.Optional[str] = None,
        output: t.Optional[OutputType] = None,
    ) -> "Wave":
        """Casts an existing ndarray to a Wave type.

        Args:
            input_array: existing ndarray
            name: optional name of the waveform in the sequencer code snippet.
            output: optional output configuration for the waveform in the
                    sequencer code snippet.

        Returns:
            Array as Wave object.
        """
        obj = np.asarray(input_array).view(cls)
        obj.name = name
        obj.output = output
        return obj

    def __array_finalize__(self, obj: t.Optional[np.ndarray]) -> None:
        if obj is None:
            return
        self.name = getattr(obj, "name", None)
        self.output = getattr(obj, "output", None)


class Waveforms(MutableMapping):
    """Waveform dictionary.

    The key specifies the slot of the waveform on the device.
    The value is a the waveform itself, represented by a tuple
    (wave1, wave2, marker).

    The value tuple(wave1, wave2=None, marker=None) consists of the following parts:
        * wave1 (array): Array with data of waveform 1.
        * wave2 (array): Array with data of waveform 2.
        * markers (array): Array with marker data.

    A helper function exist called `assign_waveform` which provides an easy way
    of assigning waveforms to slots. But one can also use the direct dictionary
    access:

    >>> wave = 1.0 * np.ones(1008)
    >>> markers = np.zeros(1008)
    >>> waveforms = Waveforms()
    >>> waveforms.assign_waveform(0, wave)
    >>> waveforms.assign_waveform(1, wave, -wave)
    >>> waveforms.assign_waveform(2, wave, -wave, markers)
    >>> waveforms.assign_waveform(3, wave, markers=markers)
    >>> waveforms[4] = (wave,)
    >>> waveforms[5] = (wave, -wave)
    >>> waveforms[6] = (wave, -wave, markers)
    >>> waveforms[7] = (wave, None, markers)

    The arrays can be provided as arrays of integer, float. The first wave also
    can be of type complex. In that case the second waveform must be `None`.

    Depending on the target format the function `get_raw_vector` converts the
    waves into the following format:

    * native AWG waveform format (interleaved waves and markers as uint16) that
      can be uploaded to the AWG waveform nodes. In case the first wave is of
      type complex the imaginary part is treated as the second wave.
    * complex waveform format that can be uploaded to the generator waveform
      nodes (does not support markers). In case two real waveforms have been
      specified they are combined into a single complex waveform, where the
      imaginary part defined by the second wave.
    """

    def __init__(self):
        self._waveforms = {}

    def __getitem__(self, slot: int) -> _Waveform:
        return self._waveforms[slot]

    def __setitem__(self, slot: int, value: t.Union[np.ndarray, _Waveform]):
        if isinstance(value, np.ndarray):
            self._set_waveform(slot, (value, None, None))
        else:
            self._set_waveform(slot, value)

    def __delitem__(self, slot: int):
        del self._waveforms[slot]

    def __iter__(self):
        return iter(self._waveforms)

    def __len__(self):
        return len(self._waveforms)

    def assign_waveform(
        self,
        slot: int,
        wave1: np.ndarray,
        wave2: t.Optional[np.ndarray] = None,
        markers: t.Optional[np.ndarray] = None,
    ) -> None:
        """Assigns a waveform to a slot.

        Args:
            slot: slot number
            wave1: Array with data of waveform 1.
            wave2: Array with data of waveform 2. (default = None)
            markers: Array with marker data. (default = None)
        """
        self._set_waveform(slot, (wave1, wave2, markers))

    def assign_native_awg_waveform(
        self,
        slot: int,
        raw_waveform: np.ndarray,
        channels: int = 1,
        markers_present: bool = False,
    ) -> None:
        """Assigns a native AWG waveform to a slot.

        Native AWG waveform = a single waveform (interleaved waves and markers
        as uint16).

        Args:
            slot: slot number
            raw_waveform: native AWG waveform.
            channels: Number of channels present in the wave. (default = 1)
            markers_present: Indicates if markers are interleaved in the wave.
                (default = False)
        """
        wave1, wave2, markers = parse_awg_waveform(
            raw_waveform,
            channels=channels,
            markers_present=markers_present,
        )
        if markers_present and channels == 2:
            self._waveforms[slot] = (wave1, wave2, markers)
        elif channels == 2:
            self._waveforms[slot] = (wave1, wave2, None)
        elif markers_present:
            self._waveforms[slot] = (wave1, None, markers)
        else:
            self._waveforms[slot] = (wave1, None, None)

    def _set_waveform(
        self,
        slot: int,
        value: _Waveform,
    ) -> None:
        """Assigns a tuple of waves to the slot.

        The passed waves are validated against the following requirements:
        * At least one wave must be defined
        * At most three waves are defined
        * The waves must by numpy arrays
        * The waves must have the same length
        * If the first wave is complex teh second wave must be None

        Raises:
            RuntimeError: If the tuple does not comply to the requirements.
        """
        if len(value) < 1 or len(value) > 3:
            raise RuntimeError(
                "Only one(complex) or two(real) waveforms (plus an optional marker) "
                f"can be specified per waveform. ({len(value)} where specified."
            )
        if (
            not isinstance(value[0], np.ndarray)
            or (
                len(value) > 2
                and value[1] is not None
                and not isinstance(value[1], np.ndarray)
            )
            or (
                len(value) > 3
                and value[1] is not None
                and not isinstance(value[2], np.ndarray)
            )
        ):
            raise RuntimeError("Waveform must be specified as numpy.arrays")
        if len(value) >= 2 and value[1] is not None and len(value[0]) != len(value[1]):
            raise RuntimeError("The two waves must have the same length")
        if len(value) == 3 and value[2] is not None and len(value[0]) != len(value[2]):
            raise RuntimeError(
                "The marker must have the same length than the waveforms"
            )
        if np.iscomplexobj(value[0]) and not (len(value) < 3 or value[1] is None):
            raise RuntimeError(
                "The first waveform is complex therefore only one "
                "waveform can be specified."
            )
        self._waveforms[slot] = tuple(
            w.view(Wave) if w is not None else None for w in value
        ) + (None,) * (3 - len(value))

    def get_raw_vector(
        self,
        slot: int,
        *,
        complex_output: bool = False,
    ) -> np.ndarray:
        """Get the raw vector for a slot required by the device.

        Either converts a waveform into the native AWG waveform format that can
        be uploaded to the AWG wave node or converts the waveform into a complex
        waveform that can be uploaded to a generator wave node.
        (complex_output = True).

        Args:
            slot: slot number of the waveform
            complex_output: Flag if the output should be a complex waveform for a
                generator node, instead of of the native AWG format that can
                only be uploaded to an AWG node. (default = False)

        Returns:
            Waveform in the native AWG format or as a complex waveform

        Raises:
            ValueError: The length of the waves does not match the target length.

        .. versionchanged:: 0.4.2

            Removed `target_length` flag and functionality. The length check is
            now done in the `validate` function.
        """
        waves = self._waveforms[slot]
        wave1 = np.zeros(1) if len(waves[0]) == 0 else waves[0]
        wave2 = np.zeros(1) if waves[1] is not None and len(waves[1]) == 0 else waves[1]
        marker = waves[2]
        if complex_output and np.iscomplexobj(wave1):
            if wave2 is not None or marker is not None:
                warnings.warn("Complex values do not support markers", RuntimeWarning)
            return wave1
        if complex_output and not np.iscomplexobj(wave1):
            if marker is not None:
                warnings.warn("Complex values do not support markers", RuntimeWarning)
            complex_wave = np.zeros(wave1.shape, dtype=np.complex128)
            complex_wave.real = wave1
            if wave2 is not None:
                complex_wave.imag = wave2
            return complex_wave

        if np.iscomplexobj(wave1):
            marker = wave2 if wave2 is not None else marker
            wave2 = wave1.imag
            wave1 = wave1.real

        return convert_awg_waveform(
            wave1,
            wave2=wave2,
            markers=marker if marker is not None else None,
        )

    def _get_waveform_sequence(self, index: int) -> str:
        """Get sequencer code snippet for a single waveform.

        The sequencer code snippet is generated with the following information:
            * Waveform length
            * Waveform index
            * presence of markers and for which channel
            * Defined names of the waveforms (if set)
            * Defined output configuration (if set)

        Returns:
            Sequencer code snippet.

        .. versionadded:: 0.3.5
        """
        waves = self._waveforms[index]
        wave_length = max(1, waves[0].size)
        w2_present = waves[1] is not None
        marker = waves[2]
        names = [waves[0].name, waves[1].name if waves[1] is not None else None]
        outputs = [waves[0].output, waves[1].output if waves[1] is not None else None]

        if np.iscomplexobj(waves[0]):
            marker = waves[1] if waves[1] is not None else marker
            w2_present = True
            names = names if not names[0] or isinstance(names[0], str) else names[0]
            outputs = (
                outputs
                if not outputs[0] or not isinstance(outputs, t.Iterable)
                else outputs[0]
            )
        marker = None if marker is None else np.unpackbits(marker.astype(np.uint8))

        def marker_to_bool(i: int) -> str:
            return "true" if np.any(marker[7 - i :: 8]) else "false"  # noqa: E203

        def to_wave_str(i: int) -> str:
            if marker is None:
                return f"placeholder({wave_length}, false, false)"
            return (
                f"placeholder({wave_length}, {marker_to_bool(i * 2)}, "
                + f"{marker_to_bool(i * 2 + 1)})"
            )

        w1_assign = to_wave_str(0)
        w2_assign = to_wave_str(1) if w2_present else ""
        w2_decl = w1_decl = ""
        if names[0]:
            w1_decl = f"wave {names[0]} = {w1_assign};\n"
            w1_assign = names[0]
        if names[1]:
            w2_decl = f"wave {names[1]} = {w2_assign};\n"
            w2_assign = names[1]
        if outputs[0]:
            if outputs[0] in [OutputType.OUT1, OutputType.OUT2]:
                w1_assign = f"{outputs[0]}, {w1_assign}"
            elif outputs[0] == OutputType.OUT1 | OutputType.OUT2:
                w1_assign = f"1, 2, {w1_assign}"
        if outputs[1]:
            if outputs[1] in [OutputType.OUT1, OutputType.OUT2]:
                w2_assign = f"{outputs[1]}, {w2_assign}"
            elif outputs[1] == OutputType.OUT1 | OutputType.OUT2:
                w2_assign = f"1, 2, {w2_assign}"

        if w2_assign:
            return (
                f"{w1_decl}{w2_decl}assignWaveIndex({w1_assign}, {w2_assign}, {index});"
            )
        return f"{w1_decl}assignWaveIndex({w1_assign}, {index});"

    def get_sequence_snippet(self) -> str:
        """Return a sequencer code snippet for the defined waveforms.

        Based on the defined waveforms and their additional information this
        function generates a sequencer code snippet that can be used to define
        the given waveforms. The following information will be used:

            * Waveform length
            * Waveform index
            * presence of markers and for which channel
            * Defined names of the waveforms (if set)
            * Defined output configuration (if set)

        Example:
            >>> waveform = Waveform()
            >>> waveform.assign_waveform(
                    0,
                    wave1=Wave(
                        np.ones(1008),
                        name="w1",
                        output=OutputType.OUT1 | OutputType.OUT2
                    ),
                    wave2=Wave(
                        -np.ones(1008),
                        name="w2",
                        output=OutputType.OUT2),
                    markers=15 * np.ones(1008),
                )
            >>> waveform.get_sequence_snippet()
            wave w1 = placeholder(1008, true, true);
            wave w2 = placeholder(1008, true, true);
            assignWaveIndex(1, 2, w1, 2, w2, 0);

        Returns:
            Sequencer Code snippet.

        .. versionadded:: 0.3.5
        """
        return "\n".join(
            [
                self._get_waveform_sequence(slot)
                for slot in sorted(self._waveforms.keys())
            ]
        )

    def validate(self, meta_info: t.Union[bytes, str], *, allow_missing=True) -> None:
        """Validates the waveforms against the ones defined in a sequencer program.

        The information about the sequencer code can either be passed in form
        of a compiled elf file or a the waveform descriptor provided by the
        device once a valid sequencer code was uploaded to the device.
        The waveform descriptor can be read from the device through the node
        `<path to awg core>.waveform.descriptors`
        (`e.g hdawg.awgs[0].waveform.descriptors()`).

        Args:
            meta_info: Compiled sequencer code or the waveform descriptor.
            allow_missing: Flag if this function allows placeholder waveforms
                to be defined in the sequencer code that are not used in this
                object. This is disabled by default since uploading/replacing
                only a fraction of the defined waveforms is a valid use case.

        Raises:
            TypeError: If the meta_info are not a compiled elf file, string or
                dictionary.
            ValidationError: If the Validation fails.

        .. versionadded:: 0.4.2
        """
        waveform_info = {}
        try:
            elf_info = ELFFile(BytesIO(meta_info))  # type: ignore[arg-type]
            raw_data = elf_info.get_section_by_name(".waveforms").data().decode("utf-8")
            waveform_info = json.loads(raw_data)["waveforms"]
        except (TypeError, ELFError) as e:
            if isinstance(meta_info, str):
                waveform_info = json.loads(meta_info)["waveforms"]
            elif isinstance(meta_info, dict):
                waveform_info = (
                    meta_info["waveforms"] if "waveforms" in meta_info else meta_info
                )
            else:
                raise TypeError(
                    "meta_info needs to be an elf file or the waveform descriptor from "
                    "the device (e.g. device.awgs[0].waveform.descriptor(). The passed "
                    f"meta_info are of type {type(meta_info)} ({str(meta_info)})."
                ) from e
        defined_wave_lengths = {
            index: wave["length"]
            for index, wave in enumerate(waveform_info)
            if wave["name"].startswith("__placeholder")
            or wave["name"].startswith("__playWave")
        }
        for index, waves in self._waveforms.items():
            if index >= len(waveform_info):
                raise IndexError(
                    f"There are {len(waveform_info)} waveforms defined on the device "
                    f"but the passed waveforms specified one with index {index}."
                )
            try:
                target_length = int(defined_wave_lengths[index])
            except KeyError as e:
                if "__filler" in waveform_info[index]["name"]:
                    raise ValidationError(
                        f"The waveform at index {index} is only "
                        "a filler and can not be overwritten."
                    ) from e
                raise ValidationError(
                    f"The waveform at index {index} is not a placeholder but of "
                    f"type {waveform_info[index]['name'].lstrip('__')[:-4]}"
                ) from e
            wave_length = max(len(waves[0]), 1)
            if wave_length != target_length:
                # Waveforms can only be to short since the compiler always rounds
                # up the length to next valid value.
                raise ValidationError(
                    f"Waveforms at index {index} are smaller than the target length "
                    f"{wave_length} < {target_length}."
                )
        if not allow_missing and len(defined_wave_lengths) > len(self._waveforms):
            missing_indexes = [
                i for i in defined_wave_lengths.keys() if i not in self._waveforms
            ]
            raise ValidationError(
                "The the sequencer code defines placeholder waveforms for the "
                f"following indexes that are missing in this object: {missing_indexes}"
            )
