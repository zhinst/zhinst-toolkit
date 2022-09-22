SHFQA
=====

The Zurich Instruments SHFQA is our second generation quantum analyzer, designed
to readout superconducting and spin qubits. It integrates frequency upconversion
to 8.5 GHz, and up to 4 readout channels that can faithfully discriminate up to
16 qubits, 8 qutrits or 5 ququads.

Please refer to the `user manual <http://docs.zhinst.com/shfqa_user_manual/overview.html>`_
for an in-depth explanation of all features.

Like every device the device specific settings and data is organized in a path
like structure called the node tree. zhinst-toolkit provides a pythonic way of
interacting with this node tree. For more information about all functionalities
and usage of the node tree in toolkit refer to the dedicated :doc:`section <../first_steps/nodetree>`.

The package ``zhinst-utils`` provided by Zurich Instruments offers a
collection of helper functions to ease the use of the SHFQA among other devices.
Toolkit embeds these functions inside the nodetree. The following table shows
the equivalent functions in zhinst-toolkit.


.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - zhinst-utils
     - zhinst-toolkit
     - info
   * - start_continuous_sw_trigger()
     - :func:`shfqa.start_continuous_sw_trigger()<zhinst.toolkit.driver.devices.shfqa.SHFQA.start_continuous_sw_trigger>`
     - Issues a specified number of software triggers.
   * - max_qubits_per_channel()
     - :func:`shfqa.max_qubits_per_channel()<zhinst.toolkit.driver.devices.shfqa.SHFQA.max_qubits_per_channel>`
     - Maximum number of supported qubits per channel.
   * - **qachannel**
     - shfqa.qachannels[n]...
     -
   * - configure_channel()
     - :func:`...configure_channel()<zhinst.toolkit.driver.devices.shfqa.QAChannel.configure_channel>`
     - Configures the RF input and output of a specified channel.
   * - **generator**
     - **shfqa.qachannels[n].generator...**
     -
   * - enable_sequencer()
     - :func:`...enable_sequencer()<zhinst.toolkit.driver.nodes.generator.Generator.enable_sequencer>`
     - Starts the sequencer of a specific channel.
   * -
     - :func:`...wait_done()<zhinst.toolkit.driver.nodes.generator.Generator.wait_done>`
     - Wait until the generator execution is finished.
   * - load_sequencer_program()
     - :func:`...load_sequencer_program()<zhinst.toolkit.driver.nodes.generator.Generator.load_sequencer_program>`
     - Compiles and loads a program to a specified sequencer.
   * - write_to_waveform_memory()
     - :func:`...write_to_waveform_memory()<zhinst.toolkit.driver.nodes.generator.Generator.write_to_waveform_memory>`
     - Writes pulses to the waveform memory.
   * -
     - :func:`...read_from_waveform_memory()<zhinst.toolkit.driver.nodes.generator.Generator.read_from_waveform_memory>`
     - Read pulses from the waveform memory.
   * - configure_sequencer_triggering()
     - :func:`...configure_sequencer_triggering()<zhinst.toolkit.driver.nodes.generator.Generator.configure_sequencer_triggering>`
     - Configure the triggering of a specified sequencer.
   * - **readout**
     - **shfqa.qachannels[n].readout...**
     -
   * - configure_result_logger_for_readout()
     - :func:`...configure_result_logger()<zhinst.toolkit.driver.nodes.readout.Readout.configure_result_logger>`
     - Configures the result logger for readout mode.
   * - enable_result_logger(mode="readout")
     - :func:`...run()<zhinst.toolkit.driver.nodes.readout.Readout.run>`
     - Reset and enable the result logger.
   * -
     - :func:`...stop()<zhinst.toolkit.driver.nodes.readout.Readout.stop>`
     - Stop the result logger.
   * -
     - :func:`...wait_done()<zhinst.toolkit.driver.nodes.readout.Readout.wait_done>`
     - Wait until readout is finished.
   * - get_result_logger_data(mode="readout")
     - :func:`...read()<zhinst.toolkit.driver.nodes.readout.Readout.read>`
     - Waits until the logger finished recording and returns the measured data.
   * - configure_weighted_integration()
     - :func:`...write_integration_weights()<zhinst.toolkit.driver.nodes.readout.Readout.write_integration_weights>`
     - Configures the weighted integration.
   * -
     - :func:`...read_integration_weights()<zhinst.toolkit.driver.nodes.readout.Readout.read_integration_weights>`
     - Read integration weights from the waveform memory.
   * - **spectroscopy**
     - **shfqa.qachannels[n].spectroscopy...**
     -
   * - configure_result_logger_for_spectroscopy()
     - :func:`...configure_result_logger()<zhinst.toolkit.driver.nodes.spectroscopy.Spectroscopy.configure_result_logger>`
     - Configures the result logger for spectroscopy mode.
   * - enable_result_logger(mode="spectroscopy")
     - :func:`...run()<zhinst.toolkit.driver.nodes.spectroscopy.Spectroscopy.run>`
     - Reset and enable the result logger.
   * -
     - :func:`...stop()<zhinst.toolkit.driver.nodes.spectroscopy.Spectroscopy.stop>`
     - Stop the result logger.
   * -
     - :func:`...wait_done()<zhinst.toolkit.driver.nodes.spectroscopy.Spectroscopy.wait_done>`
     - Wait until spectroscopy is finished.
   * - get_result_logger_data(mode="spectroscopy")
     - :func:`...read()<zhinst.toolkit.driver.nodes.spectroscopy.Spectroscopy.read>`
     - Waits until the logger finished recording and returns the measured data.
   * - **scope**
     - **shfqa.scopes[0]...**
     -
   * - configure_scope()
     - :func:`...configure()<zhinst.toolkit.driver.nodes.shfqa_scope.SHFScope.configure>`
     - Configures the scope for a measurement.
   * -
     - :func:`...run()<zhinst.toolkit.driver.nodes.shfqa_scope.SHFScope.run>`
     - Run the scope recording.
   * -
     - :func:`...stop()<zhinst.toolkit.driver.nodes.shfqa_scope.SHFScope.stop>`
     - Stop the scope recording.
   * -
     - :func:`...wait_done()<zhinst.toolkit.driver.nodes.shfqa_scope.SHFScope.wait_done>`
     - Wait until the Scope recording is finished.
   * - get_scope_data()
     - :func:`...read()<zhinst.toolkit.driver.nodes.shfqa_scope.SHFScope.read>`
     - Read out the recorded data from the scope.


The following examples give a brief overview of how the SHFQA can be used in
zhinst-toolkit.

.. toctree::
   :maxdepth: 2

   shfqa_qubit_readout_measurement
   shfqa_qubit_readout_weights
   shfqa_sweeper
   shfqa_multistate_discrimination

