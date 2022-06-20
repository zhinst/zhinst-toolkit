PQSC
=====

The Zurich Instruments PQSC Programmable Quantum System Controller brings
together the instrumentation required for quantum computers with up to 100
qubits. Its ZSync low-latency, real-time communication links are designed
specifically for quantum computing: the PQSC overcomes the practical limitations
of traditional control methods, making automated and rapid qubit calibration
routines a reality. Programming access to the powerful Xilinx UltraScale+ FPGA
is the basis for developing new and optimized processing solutions for rapid
tune-up and error correction adapted to the specific algorithm and computer
architecture in use.

Please refer to the `user manual <http://docs.zhinst.com/pqsc_user_manual/overview.html>`_
for an in-depth explanation of all features.

Like every device the device specific settings and data is organized in a path
like structure called the node tree. zhinst-toolkit provides a pythonic way of
interacting with this node tree. For more information about all functionalities
and usage of the node tree in toolkit refer to the dedicated
:doc:`section <../first_steps/nodetree>`.

zhinst-toolkit offers the following helper functions for the PQSC:

.. list-table::
   :header-rows: 1

   * - Helper Function
     - Info
   * - :func:`pqsc.arm()<zhinst.toolkit.driver.devices.pqsc.PQSC.arm>`
     - Prepare PQSC for triggering the instruments.
   * - :func:`pqsc.run()<zhinst.toolkit.driver.devices.pqsc.PQSC.run>`
     - Start sending out triggers.
   * - :func:`pqsc.arm_and_run()<zhinst.toolkit.driver.devices.pqsc.PQSC.arm_and_run>`
     - Arm the PQSC and start sending out triggers.
   * - :func:`pqsc.stop()<zhinst.toolkit.driver.devices.pqsc.PQSC.stop>`
     - Stop the trigger generation.
   * - :func:`pqsc.wait_done()<zhinst.toolkit.driver.devices.pqsc.PQSC.wait_done>`
     - Wait until trigger generation and feedback processing is done.
   * - :func:`pqsc.check_ref_clock()<zhinst.toolkit.driver.devices.pqsc.PQSC.check_ref_clock>`
     - Check if reference clock is locked successfully.
   * - :func:`pqsc.check_zsync_connection()<zhinst.toolkit.driver.devices.pqsc.PQSC.check_zsync_connection>`
     - Check if the ZSync connection on the given port is successful.

