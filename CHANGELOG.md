# zhinst-toolkit Changelog

## Version 0.6.2
* The function `enable_qccs_mode` of the HDAWG driver now accept an optional argument to select the QCCS generation.
  It's advised to set it to 2 (gen2) when the HDAWG is operated with PQSC together with SHF instruments, and set it
  to 1 (gen1) when the HDAWG is operated with PQSC together with UHFQA instruments.
* Improved `CommandTable` performance when `CommandTable.active_validation` is disabled.
* Added `CommandTable.is_valid()` method to check validity of the command table.
* Added `py.typed` type information marker file.
* Add command table property to the sequencer class to have a simple way to store them together.

## Version 0.6.1
* Deep gets on nodes with keywords returns an enum like the regular get.
* Fix rare failures of `wait_for_state_change` function that resulted in early timeouts.
* All keywords on nodes are correctly supported, and not only the first one for each option.
* Function `wait_for_state_change` now supports strings and enums for keywords nodes.
* Fix #252. ListNodes now also supports numpy integer types as index argument.
* The function `check_zsync_connection` of PQSC now raise an error if the port is in a faulty
  state, instead of return False.

## Version 0.6.0
* Revert full support of `fnmatch` wildcards and instead use the LabOne wildcard support.
  This means only `*` symbols are supported. A `*` in the middle of the path matches
  everything instead of a `/`. A `*` at the end of the path matches everything.
* Fix problem of garbage collection daq sessions. The problem was caused due to using
  lru caches for instance methods. The usage of lru cache has now been bypassed or
  replaced with the `functools.cached_property` decorator (which is currently copied
  to ensure support for python 3.7).
* `device.factory_reset` now raises an exception if the factory reset was not successful (`#243`).
* Fixed issue where calling a `Node` with `dir()` returned duplicate values on some nodes.
* Factory preset is now available for SHFSG, SHFQA, SHFQA devices (`#249`).

## Version 0.5.3
* Add internal trigger to SHFQA sweeper class.

## Version 0.5.2
* Add SHFQA / SHFQC Power Spectral Density (PSD) node and example

## Version 0.5.1
* Added full support for the following LabOne modules (no need to fallback to `zhinst.core`):
  * Impedance Module
  * Precompensation Advisor Module
* Introduced new base exception class `zhinst.toolkit.exceptions.ToolkitError`, deriving from `RuntimeError`.
   * Changed some `RuntimeError` exceptions to `ToolkitError`.
* Added `find_zsync_worker_port()` to `PQSC` device class.
  The function can be used to find the ID of the PQSC ZSync port connected to a given device.
* Added `session` property to `BaseInstrument`. This enables getting the given `Session` from the instrument.
* Changed SHFQA node `qachannels/*/oscs/0/freq` value range from (-500e6 Hz, 500e6 Hz) to (-1e9 Hz, 1e9 Hz). Out-of-range values now rounds
  to (-1e9 Hz, 1e9 Hz). The functionality is changed to be consistent with LabOne UI.
* Improved verbosity of the error message when invalid attributes of `CommandTable.header` and `CommandTable.table` are used.
* Fix issue with downloading waveforms from the device. This issue prevented indexes larger than 9 to be read from the device.

## Version 0.5.0
* Added full support for the following LabOne modules (no need to fallback to zhinst.core):
  * Scope Module
  * Sweeper Module
  * DAQ Module
* Renamed `zhinst.toolkit.nodetree.node.WildcardResult` to `zhinst.toolkit.nodetree.helpers.NodeDict`
* Added `active_validation` argument to `CommandTable`. By disabling it, `CommandTable` does not actively
  validate the inputs and therefore it improves the speed for command table creation.
* Adapt `awg.enable_sequencer` to check the acknowledged value instead of using `wait_for_state_change`. This makes it much more stable when used with short sequences.
* Fix issue with downloading waveforms from the device. This issue prevented reading waveforms from any other than the base channel.
* Normalize the `zhinst-core` dependency version.
* Update SHFQA Sweeper to expose new properties through nodes (`predicted_cycle_time`, `actual_hold_off_time`, `actual_settling_time`)
* Tested against Python 3.11

## Version 0.4.3
* Fix issue that prevented correct compilation of sequences for AWG cores other than the first one.

## Version 0.4.2
* Embed multistate utils for the SHFQA into the node tree
  * shfqa.qachannels[n].readout.multistate.qudits[m].configure(settings)
  * shfqa.qachannels[n].readout.multistate.get_qudits_results()
* Added new example for the multistate discrimination (shfqa_multistate_discrimination) for the SHFQA
* Fixed issue `#181` (Wrong _device_type of awg node of UHFQA/UHFLI) which prevented
  the compilation of sequences.
* Waveform validation moved from the `write_to_waveform_memory` into `Waveforms.validate`
* Command Table `$schema` key removed from the output of `CommandTable.as_dict` function
* Command Table validation changed to disabled by default
* Command Table upload check disabled when called within a transaction.
* New dependency `pyelftools` for extracting waveform information from a complied
  sequencer code.
* Interface auto detection adapted to support `none`, which was introduced with LabOne 22.08

## Version 0.4.1
* For all LabOne modules forward the `execute` function from the zhinst-core in zhinst-toolkit

## Version 0.4.0
* Add new class `zhinst.toolkit.Sequence` that allows a more flexible use of
  sequences in toolkit (`#141`).
* Add support for session wide transactions that bundle set command from all
  devices connected to the data server. (`#134`)
* Add `from_existing_connection()` to `zhinst.toolkit.Session` to help reusing the existing DataServer connection.
* Bugfix: Nodes with nameless options don't raise an exception when their enum attribute is called (`#165`).
* Bugfix: Values of enumerated nodes can now be pickled (`#129`).
* Bugfix: `SHFScope` `run()`  and `stop()` shows specified timeout value when `TimeoutError` is raised.
* Bugfix: Allow capital letters in node paths. (`#173`).
* Adapt toolkit to use the offline awg compiler when uploading a sequencer code to
  a awg node. Improves the performance a lot and also enables the uploading of
  a sequencer code within a transaction (Works both for AWGs and Generators).
* Add new function `compile_sequencer_code` to the awg node.

## Version 0.3.5
* Adapt AWG Waveform upload (`write_to_waveform_memory`) to append to existing transactions.
* Make consistency validate during waveform upload optional (new flag `validate` in `write_to_waveform_memory`).
* Add `get_sequence_snippet` function to `zhinst.toolkit.Waveforms` class.
  The function is able to generated a sequence code snippet that defines and assigns
  the waveforms for this object. Additional meta information like an optional name
  or the output configuration can be specified through a newly added `Wave` class from `zhinst.toolkit.Waveforms`.
* Getting a value by calling a wildcard node now returns `zhinst.toolkit.nodetree.node.WildcardResult`


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
* Bugfix: Adapt Node Tree to be able to get daq result data #113
* Bugfix: in the ``Waveform`` class to be able to convert a single waveform into
  a complex waveform.
* Bugfix: HF2 PID nodes are available.

## Version 0.3.1
* Add missing nodes setting for QCCS mode #108
* pqsc.check_zsync_connection blocks even if nothing is connected
* Create a temporary awg module every time a sequencer code is uploaded
  (The reason for it is to have de defined state) #104
* reintroduce uhfqa.qa_delay function
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
* Adapt modulation frequency range to +-1GHz
  (shfsg.sgchannels[i].modulation_freq, shfqa.qachannels[i].sweeper.oscillator_freq)
* Bugfix: DAQ module timeout exception raises AttributeError

## Version 0.2.3
* Make the command table validation optional

## Version 0.2.2
* SHFQA Adapt oscillator_freq to +-500e6 Hz
* Initial support for SHFSG
* Make Node Tree generation case insensitive

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
* Initial release
