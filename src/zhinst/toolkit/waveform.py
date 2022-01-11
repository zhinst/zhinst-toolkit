"""Dictionary like waveform representation."""
import typing as t
import warnings
from collections.abc import MutableMapping

import numpy as np
from zhinst.utils import convert_awg_waveform, parse_awg_waveform

NumpyArray = t.TypeVar("NumpyArray")


class Waveforms(MutableMapping):
    """Waveform dictionary

    The key specifies the slot of the waveform on the device.
    The value is a the waveform itself, represented by a tuple
    (wave1, wave2, marker).

    The value tuple(wave1, wave2=None, marker=None) consists of the follwing parts:
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

    The arrays can be provided as arrays of interger, float. The first wave also
    can be of type complex. In that case the second waveform must be None.

    Depending on the target format the function `get_raw_vector` converts the
    waves into the following format:

    * native AWG waveform format (interleaved waves and markers as uint16) that
      can be uploaded to the awg waveform nodes. In case the first wave is of
      type complex the imag part is treated as the second wave.
    * complex waveform format that can be uploaded to the generator waveform
      nodes (does not support markers). In case two real waveforms have been
      specified they are combined into a single complex waveform, where the
      imaginary part defined by the second wave.
    """

    def __init__(self):
        self._waveforms = {}

    def __getitem__(self, slot: int) -> t.Tuple[NumpyArray, NumpyArray, NumpyArray]:
        return self._waveforms[slot]

    def __setitem__(self, slot: int, value: t.Tuple[NumpyArray, ...]):
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
        wave1: NumpyArray,
        wave2: NumpyArray = None,
        markers: NumpyArray = None,
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
        raw_waveform: NumpyArray,
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
            markers: Indicates if markers are interleaved in the wave.
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

    def _set_waveform(self, slot: int, value: t.Tuple[NumpyArray, ...]) -> None:
        """Assigns a tuple of waves to the slot.

        The passed waves are validated against the following requirements:
        * At least one wave must be defined
        * At most thre waves are defined
        * The waves must by numpy arrays
        * The waves must have the same length
        * If the first wave is complex teh second wave must be None

        Raises:
            RuntimeError: If the tuple does not comply to the requirements.
        """
        if len(value) < 1 or len(value) > 3:
            raise RuntimeError(
                "Only one(complex) or two(real) waveforms (plus an optional marker) "
                f"can be specified per Waveform. ({len(value)} where specified."
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
            raise RuntimeError("waveform must be specified as numpy.arrays")
        if len(value) >= 2 and value[1] is not None and len(value[0]) != len(value[1]):
            raise RuntimeError("The two waves must have the same length")
        if len(value) == 3 and value[2] is not None and len(value[0]) != len(value[2]):
            raise RuntimeError(
                "The marker must have the same length than the waveforms"
            )
        if np.iscomplexobj(value[0]) and not (len(value) < 3 or value[1] is None):
            raise RuntimeError(
                "the first waveform is complex therfore only one "
                "waveform can be specified."
            )

        self._waveforms[slot] = value + (None,) * (3 - len(value))

    def get_raw_vector(
        self, slot: int, *, target_length: int = None, complex_output: bool = False
    ) -> NumpyArray:
        """Get the raw vector for a slot required by the device.

        Either converts a waveform into the native AWG waveform format that can
        be uploaded to the AWG wave node or converts the waveform into a complex
        waveform that can be uploaded to a generator wave node.
        (complex_output = True).

        Args:
            slot: slot number of the waveform
            target_length: target length of the output waveform. If
                specified the waves and markers will have the specified length
                (e.g. wave1, wave2 and markers are specified the resulting
                waveform will have the length 3*target_length). (default = None)
            complex_output: Flag if the output should be a complex waveform for a
                generator node, instead of of the native AWG format that can
                only be uploaded to an AWG node. (default = False)

        Returns:
            Waveform in the native AWG format or as a complex waveform

        Raises:
            ValueError: The length of the waves does not matche the target
                length.
        """
        waves = self._waveforms[slot]
        wave1 = np.zeros(1) if len(waves[0]) == 0 else waves[0]
        wave2 = np.zeros(1) if waves[1] is not None and len(waves[1]) == 0 else waves[1]
        marker = waves[2]

        if target_length and len(wave1) > target_length:
            raise ValueError(
                f"waveforms are larger than the target length "
                f"{len(wave1)} > {target_length}."
            )
        if target_length and len(wave1) < target_length:
            raise ValueError(
                f"waveforms are smaller than the target length "
                f"{len(wave1)} < {target_length}."
            )

        if complex_output and np.iscomplexobj(wave1):
            if wave2 is not None or marker is not None:
                warnings.warn("Complex values do not support markers", RuntimeWarning)
            return wave1
        if complex_output and not np.iscomplexobj(wave1):
            if marker is not None:
                warnings.warn("Complex values do not support markers", RuntimeWarning)
            complex_wave = np.empty(wave1.shape, dtype=np.complex128)
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
