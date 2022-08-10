SHFSG
=====

The Zurich Instruments SHFSG Signal Generator produces qubit control signals in
the frequency range from DC to 8.5 GHz with a spurious-free modulation bandwidth
of 1 GHz. The SHFSG uses a double superheterodyne technique for frequency
up-conversion, which eliminates the need for mixer calibration and saves time on
system tune-up. Each SHFSG comes with 4 or 8 analog output channels with 14-bit
vertical resolution.

Please refer to the `user manual <http://docs.zhinst.com/shfsg_user_manual/overview.html>`_
for an in-depth explanation of all features.

Like every device the device specific settings and data is organized in a path
like structure called the node tree. zhinst-toolkit provides a pythonic way of
interacting with this node tree. For more information about all functionalities
and usage of the node tree in toolkit refer to the dedicated :doc:`section <../first_steps/nodetree>`.

The package ``zhinst-utils`` provided by Zurich Instruments offers a
collection of helper functions to ease the use of the SHFSG among other devices.
Toolkit embeds these functions inside the nodetree. The following table shows
the equivalent functions in zhinst-toolkit.


.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - zhinst-utils
     - zhinst-toolkit
     - info
   * - **sgchannel**
     - **shfsg.sgchannels[n]...**
     -
   * - configure_channel()
     - :func:`...configure_channel<zhinst.toolkit.driver.devices.shfsg.SGChannel.configure_channel>`
     - Configures the RF input and output of a specified channel.
   * - configure_pulse_modulation()
     - :func:`...configure_pulse_modulation<zhinst.toolkit.driver.devices.shfsg.SGChannel.configure_pulse_modulation>`
     - Configure the pulse modulation.
   * - configure_sine_generation()
     - :func:`...configure_sine_generation<zhinst.toolkit.driver.devices.shfsg.SGChannel.configure_sine_generation>`
     - Configures the sine generator output.
   * -
     - :func:`...awg_modulation_freq<zhinst.toolkit.driver.devices.shfsg.SGChannel.awg_modulation_freq>`
     - Modulation frequency of the AWG (Depends on the selected oscillator).
   * - **AWG**
     - **shfsg.sgchannels[n].awg...**
     -
   * - configure_marker_and_trigger()
     - :func:`...configure_marker_and_trigger()<zhinst.toolkit.driver.devices.shfsg.AWGCore.configure_marker_and_trigger>`
     - Configures the trigger inputs and marker outputs of the AWG.

In addition to the above mentioned ``zhinst-utils`` function the SHFSG
also supports the :doc:`common AWG <awg>` functionalities.

The following examples give a brief overview of how the SHFSG can be used in
zhinst-toolkit.

.. toctree::
   :maxdepth: 2

   shfsg_rabi
   shfsg_sine
