"""UHFQA Instrument Driver."""

import typing as t
import numpy as np

from zhinst.toolkit.driver.devices import UHFLI
from zhinst.toolkit.nodetree import Node, NodeTree
from zhinst.toolkit.nodetree.helper import (
    create_or_append_set_transaction,
    lazy_property,
)
from zhinst.toolkit.nodetree.node import NodeList


Numpy2DArray = t.TypeVar("Numpy2DArray")


class QAS(Node):
    """Quantum Analyser Channel for the UHFQA.

    Args:
        root: Underlying node tree.
        tree: tree (node path as tuple) of the coresponding node.
    """

    def __init__(
        self,
        root: NodeTree,
        tree: tuple,
    ):
        super().__init__(root, tree)

    def crosstalk_matrix(self, matrix: Numpy2DArray = None) -> t.Optional[Numpy2DArray]:
        """Sets or gets the crosstalk matrix of the UHFQA as a 2D array.

        Args:
            matrix: The 2D matrix used in the digital signal
                processing path to compensate for crosstalk between the
                different channels. The given matrix can also be a part
                of the entire 10 x 10 matrix. Its maximum dimensions
                are 10 x 10 (default: None).

        Returns:
            If no argument is given the method returns the current
            crosstalk matrix as a 2D numpy array.

        Raises:
            ValueError: If the matrix size exceeds the maximum size of
                10 x 10

        """
        if matrix is None:
            m = np.zeros((10, 10))
            for r in range(10):
                for c in range(10):
                    m[r, c] = self.crosstalk.rows[r].cols[c]()
            return m
        else:
            rows, cols = matrix.shape
            if rows > 10 or cols > 10:
                raise ValueError(
                    f"The shape of the given matrix is {rows} x {cols}. "
                    "The maximum size is 10 x 10."
                )
            for r in range(rows):
                for c in range(cols):
                    self.crosstalk.rows[r].cols[c](matrix[r, c])

    def adjusted_delay(self, value: int = None) -> int:
        """Set or get the adjustment in the quantum analyzer delay.

        Adjusts the delay that defines the time at which the integration starts
        in relation to the trigger signal of the weighted integration units.

        Depending if the deskew matrix is bypassed there exists a different
        default delay. This function can be used to add an additional delay to
        the default delay.

        Args:
            value: Number of additional samples to adjust the delay. If not
                specified this function will just return the additional delay
                currently set.

        Returns:
            The adjustment in delay in units of samples.

        Raises:
            ValueError: If the adjusted quantum analyzer delay is outside the
                allowed range of 1021 samples.

        """
        # The default delay value is defined by wether the deskew matrix is
        # bypassed or not.
        default_delay = 184 if self.bypass.deskew() else 200
        if value is None:
            return self.delay() - default_delay
        # Round down to greatest multiple of 4, as in LabOne.
        qa_delay_user = int(value // 4) * 4
        # Calculate final value of adjusted QA delay.
        qa_delay_adjusted = qa_delay_user + default_delay
        # Check if final delay is between 0 and 1020.
        if qa_delay_adjusted not in range(0, 1021):
            raise ValueError(
                "The quantum analyzer delay is out of range (0 <= "
                f"{qa_delay_user} + {default_delay} <= 1021)"
            )
        # Write the adjusted delay value to the node.
        self.delay(qa_delay_adjusted)
        return qa_delay_user


class UHFQA(UHFLI):
    """High-level driver for the Zurich Instruments UHFQA."""

    def enable_qccs_mode(self) -> None:
        """Configure the instrument to work with PQSC.

        This method sets the reference clock source and DIO settings
        correctly to connect the instrument to the PQSC.

        Info:
            Use ``factory_reset`` to reset the changes if necessary
        """
        with create_or_append_set_transaction(self._root):
            # Use external 10 MHz clock as reference
            self.system.extclk("external")
            # Configure DIO to be used in a QCCS
            # Clock DIO internally with a frequency of 50 MHz
            self.dios[0].extclk("internal")
            # Set DIO output values to QA results compatible with QCCS
            self.dios[0].mode("qa_result_qccs")
            # Drive the two least significant bytes of the DIO port
            self.dios[0].drive(0b0011)
            # Set correct DIO triggering in the AWG sequencer
            self.awgs[0].dio.strobe.slope('off')
            self.awgs[0].dio.valid.index(16)
            self.awgs[0].dio.valid.polarity('high')

    @lazy_property
    def qas(self) -> t.Sequence[QAS]:
        """A Sequence of QAS"""
        return NodeList(
            [
                QAS(self.root, self._tree + ("qas", str(i)))
                for i in range(len(self["qas"]))
            ],
            self._root,
            self._tree + ("qas",),
        )
