# zi-driver

See examples for more ...

use pip install:
```
pip install -e zi-drivers
```


### `example_multi_device.py`

Control two devices at once, HDAWG and UHFQA. Sequence on HD in "Send Trigger" mode and on QA in "External Trigger". Play Rabi sequence on with readout from QA.

### `example_Rabi-T1-T2.py`:

Loops over Rabi, T1 and T2* sequence.


### `example_waveform_upload.py`:

In "Simple" mode: queue waveforms and upload them all at once.



# Class Diagram


```mermaid

classDiagram

    HDAWG --|> Device
    HDAWG *-- AWG
    UHFQA --|> Device
    UHFQA *-- AWG
    BaseController *-- Device
    BaseController *-- ZIDeviceConnection
    BaseController *-- InstrumentConfiguration
    AWGController --|> BaseController
    AWGController *-- Compiler
    Compiler *-- SequenceProgram
    SequenceProgram *-- Sequence
    SimpleSequence --|> Sequence
    RabiSequence --|> Sequence
    T1Sequence --|> Sequence
    T2Sequence --|> Sequence

    
    class Device{
        +name
        +serial
        +interface
    }
    class HDAWG{
        +List~AWG~awgs
    }
    class UHFQA{
        +~AWG~awg
    }
    class AWG{
        +parent
        +index
        +waveforms
        +program
    }

    class BaseController{
        -connection
        -config
        -device
        +setup()
        +connect_device()
        +set()
        +get()
        +get_nodetree()  
    }
    
    class ZIDeviceConnection{
        -details
        -daq
        -awg_module
        +connect()
        +connect_device()
        +set()
        +get()
        +list_nodes()  
    }
    class InstrumentConfiguration{
        +api_config
        +instrument_config
    }

    class AWGController{
        -compiler
        +awg_compile()
        +awg_run()
        +awg_stop()
        +awg_queue_waveform()
        +awg_set_sequence_parameter()
    }

    class Compiler{
        -List~SequenceProgram~sequences
        -~Device~device
        +add_device()
        +set_parameter()
        +get_program()
    }
    
    class SequenceProgram{
        -sequence_type
        -~Sequence~sequence
    }

    class Sequence
    class SimpleSequence
    class RabiSequence
    class T1Sequence
    class T2Sequence


```





