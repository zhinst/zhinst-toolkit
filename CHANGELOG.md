# zhinst-toolkit Changelog

## Version 0.3.4

* `Commandtable.load_validation_schema` can also get the command table
  JSON schema from the device.
* ``load_sequencer_program`` now raises an ``ValueError`` 
  if empty ``sequencer_program`` string is given. :issue:`138`
* Added a new `raise_for_invalid_node` keyword-argument to ``NodeTree.update_nodes``. :issue:`110`
  
  Now only a warning (instead of ``KeyError``) is issued when trying to initialize device/module object, which does
  not have nodes defined in node value parsers.

* Minor type hint fixes. :pr:`#147`

## Version 0.3.3

* Added support for SHFQC

## Version 0.3.2
* Added a helper function ``uhfqa.qas[n].integration.write_integration_weights`` for
  QAS integration weights configuration
* Bugfix: Adapt nodetree to be able to get daq result data #113
* Bugfix: in the ``Waveform`` class to be able to convert a single waveform into
  a complex waveform.
* Bugfix: HF2 PID nodes are available.

## Version 0.3.1
* Add missing nodes setting for QCCS mode #108
* pqsc.check_zsync_connection blocks even if nothing is connected
* Create a temporary awg module every time a sequencer code is uploaded
  (The reason for it is to have de defined state) #104
* reintroduce uhfqa.qa_deleay function
* uhfli/uhfqa return node object for ``uhfli.awg`` instead of raising an error
  (necessary for qcodes drivers) #102
* ``hdawg.enable_qccs_mode`` wrong reference clock source fixed
* Small docstring corrections

## Version 0.3
* **Redesign and complete refactoring of zhinst-toolkit**
  * Lazy node tree to improve setup times
  * Switch to session based approach (no longer device based)
  * Command table handling improved
  * Waveform handling improved
  * Removed automated sequencer code generation
  * Added LabOne modules
* Improved testing with mocking

## Version 0.2.4
* Adapt modulation frequence range to +-1GHz
  (shfsg.sgchannels[i].modulation_freq, shfqa.qachannels[i].sweeper.oscillator_freq)
* Bugfix: DAQ module timout exception raises AttributeError

## Version 0.2.3
* Make the command table validation optional

## Version 0.2.2
* SHFQA Adapt oscillator_freq to +-500e6 Hz
* Initial support for SHFSG
* Make nodetree generation case insensitive

## Version 0.2.1
* Bugfix #86

## Version 0.2.0
* Python 3.8 support
* General
    * Add `sync` function used as `hdawg.sync()` to perform global synchronization
    * Add support for `syncSet`
    * Add support for `setVector`
    * Add support for loading factory presets
    * General documentation improvements
* AWG Core
    * Update sequencer commands
    * Update triggering in predefined sequences
    * Update sequencer programs
* UHFQA
    * Add `qa_delay`, `allowed_sequences` , `allowed_trigger_modes` parameter
    * Add support for PQSC
    * Add scope module
* HDAWG
    * Add `allowed_sequences` , `allowed_trigger_modes` parameter
    * Add support for PQSC
    * Add command table support
* Add PQSC driver
* Add SHFQA driver

## Version 0.1.5
* fix error when the device serial is uppercase

## Version 0.1.4
* fix busy error on AWG program upload

## Version 0.1.3
* extend AWG upload timeout to 100 s

## Version 0.1.2
* add type hints
* more documentation

## Version 0.1.1
* more documentation
* minor fixes and additions

## Version 0.1.0
* Intial release


