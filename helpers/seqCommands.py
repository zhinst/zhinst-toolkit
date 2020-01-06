from datetime import datetime


class SeqCommand(object):
    @staticmethod
    def header_comment(sequence_type="None"):
        now = datetime.now()
        return (
            "// Zurich Instruments sequencer program\n"
            "// sequence type:              {}\n"
            "// automatically generated:    {}\n\n"
        ).format(sequence_type, now.strftime("%d/%m/%Y @%H:%M"))

    @staticmethod
    def repeat(i):
        if i < 0:
            raise ValueError("Invalid number of repetitions!")
        return "\nrepeat({}){{\n\n".format(i)

    @staticmethod
    def new_line():
        return "\n"

    @staticmethod
    def comment_line():
        return "//\n"

    @staticmethod
    def wait(i):
        if i < 0:
            raise ValueError("Wait time cannot be negative!")
        if i == 0:
            return ""
        else:
            return "wait({});\n".format(int(i))

    @staticmethod
    def wait_wave():
        return "waitWave();\n"

    @staticmethod
    def trigger(value, index=1):
        if value not in [0, 1]:
            raise ValueError("Invalid Trigger Value!")
        if index not in [1, 2]:
            raise ValueError("Invalid Trigger Index!")
        return "setTrigger({});\n".format(value << (index-1))

    @staticmethod
    def count_waveform(i, n):
        return "// waveform {} / {}\n".format(i + 1, n)

    @staticmethod
    def play_wave():
        return "playWave(w_1, w_2);\n"

    @staticmethod
    def play_wave_scaled(amp1, amp2):
        if abs(amp1) > 1 or abs(amp2) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return "playWave({}*w_1, {}*w_2);\n".format(amp1, amp2)

    @staticmethod
    def play_wave_indexed(i):
        return "playWave(w{}_1, w{}_2);\n".format(i + 1, i + 1)

    @staticmethod
    def play_wave_indexed_scaled(amp1, amp2, i):
        if abs(amp1) > 1 or abs(amp2) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return "playWave({}*w{}_1, {}*w{}_2);\n".format(amp1, i + 1, amp2, i + 1)

    @staticmethod
    def init_buffer_indexed(length, i):
        if length < 16 or i < 0:
            raise ValueError("Invalid Values for waveform buffer!")
        if length % 16 != 0:
            raise ValueError("Buffer Length has to be multiple of 16!")
        return (
            "wave w{}_1 = randomUniform({});\n" "wave w{}_2 = randomUniform({});\n"
        ).format(i + 1, length, i + 1, length)

    @staticmethod
    def init_gauss(gauss_params):
        length, pos, width = gauss_params
        return (
            "wave w_1 = gauss({}, {}, {});\n" "wave w_2 = drag({}, {}, {});\n"
        ).format(length, pos, width, length, pos, width)

    @staticmethod
    def init_gauss_scaled(amp, gauss_params):
        length, pos, width = gauss_params
        if abs(amp) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return (
            "wave w_1 = {} * gauss({}, {}, {});\n" "wave w_2 = {} * drag({}, {}, {});\n"
        ).format(amp, length, pos, width, amp, length, pos, width)

    @staticmethod
    def close_bracket():
        return "\n}"

    @staticmethod
    def wait_dig_trigger(index=0):
        if index not in [0, 1, 2]:
            raise ValueError("Invalid Trigger Index!")
        if index == 0:
            return "waitDigTrigger(1);"
        else:
            return "waitDigTrigger({}, 1);\n".format(index)
