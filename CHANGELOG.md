# zhinst-toolkit Changelog

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


