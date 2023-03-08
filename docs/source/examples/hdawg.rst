HDAWG
=====

The Zurich Instruments HDAWG multi-channel Arbitrary Waveform Generator has the
highest channel density available in its class, and is designed for advanced
signal generation up to 750 MHz bandwidth. The HDAWG comes with either 4 or 8
DC-coupled, single-ended analog output channels with 16-bit vertical resolution.
Output switching is supported between a direct mode with maximized bandwidth and
superior noise performance and an amplified mode that boosts the signal amplitude
to a maximum of 5 Vpp.

Please refer to the `user manual <http://docs.zhinst.com/hdawg_user_manual/overview.html>`_
for an in-depth explanation of all features.

Like every device, the device specific settings and data is organized in a path
like structure called the node tree. zhinst-toolkit provides a pythonic way of
interacting with this node tree. For more information about all functionalities
and usage of the node tree in toolkit refer to the dedicated section
:doc:`section <../first_steps/nodetree>`.

zhinst-toolkit offers the following helper functions for the HDAWG:

.. list-table::
   :header-rows: 1

   * - Helper Function
     - Info
   * - :func:`hdawg.enable_qccs_mode()<zhinst.toolkit.driver.devices.hdawg.HDAWG.enable_qccs_mode>`
     - Configure the instrument to work with PQSC. This method sets the reference
       clock source to connect the instrument to the PQSC.

In addition to the above mentioned helper function the HDAWG
also supports the :doc:`common AWG <awg>` functionalities.

The following examples give a brief overview of how the HDAWG can be used in
zhinst-toolkit.

.. toctree::
   :maxdepth: 2

   hdawg_precomp_curve_fit