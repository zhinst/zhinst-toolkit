UHFQA
=====

The Zurich Instruments UHFQA Quantum Analyzer is a unique instrument for
parallel readout of up to 10 superconducting or spin qubits with highest speed
and fidelity. The UHFQA operates on a frequency span of up to ±600 MHz with
nanosecond timing resolution, and it features 2 signal inputs and outputs for IQ
base-band operation. Thanks to its low-latency signal processing chain of
matched filters, real-time matrix operations, and state discrimination, the
UHFQA supports the development of ambitious quantum computing projects for 100
qubits and more.

Please refer to the `user manual <http://docs.zhinst.com/uhfqa_user_manual/overview.html>`_
for an in-depth explanation of all features.

Like every device the device specific settings and data is organized in a path
like structure called the node tree. zhinst-toolkit provides a pythonic way of
interacting with this node tree. For more information about all functionalities
and usage of the node tree in toolkit refer to the dedicated
:doc:`section <../first_steps/nodetree>`.

zhinst-toolkit offers the following helper functions for the UHFQA:

.. list-table::
   :header-rows: 1

   * - Helper Function
     - Info
   * - :func:`uhfqa.enable_qccs_mode()<zhinst.toolkit.driver.devices.uhfqa.UHFQA.enable_qccs_mode>`
     - Configure the instrument to work with PQSC. This method sets the
       reference clock source and DIO settings correctly to connect the
       instrument to the PQSC.
   * - :func:`uhfqa.qas[n].crosstalk_matrix()<zhinst.toolkit.driver.devices.uhfqa.QAS.crosstalk_matrix>`
     - Sets or gets the crosstalk matrix of the UHFQA as a 2D array

In addition to the above mentioned helper function the UHFQA
also supports the :doc:`common AWG <awg>` functionalities.

The following examples give a brief overview of how the UHFQA can be used in
zhinst-toolkit.

.. toctree::
   :maxdepth: 2

   uhfqa_result_unit