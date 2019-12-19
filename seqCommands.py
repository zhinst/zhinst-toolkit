class SeqCommand(object):
    @staticmethod
    def repeat(i):
        if i < 0:
            raise ValueError("Invalid number of repetitions!")
        return "repeat({}){{".format(i)

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
        return "wait({});\n".format(int(i))

    @staticmethod
    def wait_wave():
        return "waitWave();\n"

    @staticmethod
    def trigger(i):
        if i not in [0, 1]:
            raise ValueError("Invalid Trigger Value!")
        return "setTrigger({});\n".format(i)

    @staticmethod
    def count_waveform(i, n):
        return "// waveform {} / {}\n".format(i, n)

    @staticmethod
    def play_wave_scaled(amp1, amp2):
        if abs(amp1) > 1 or abs(amp2) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return "playWave({}*w_1, {}*w_2);\n".format(amp1, amp2)

    @staticmethod
    def play_wave_indexed(i):
        return "playWave(w{}_1, w{}_2);\n".format(i, i)

    @staticmethod
    def play_wave_indexed_scaled(amp1, amp2, i):
        if abs(amp1) > 1 or abs(amp2) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return "playWave({}*w{}_1, {}*w{}_2);\n".format(amp1, i, amp2, i)

    @staticmethod
    def init_buffer_indexed(length, i):
        if length < 16 or i < 0:
            raise ValueError("Invalid Values for waveform buffer!")
        return (
            "wave w{}_1 = randomUniform({});\n" "wave w{}_2 = randomUniform({});\n"
        ).format(i, length, i, length)

    @staticmethod
    def init_gauss(length, pos, width):
        return (
            "wave w_1 = gauss({}, {}, {});\n" "wave w_2 = gauss({}, {}, {});\n"
        ).format(length, pos, width, length, pos, width)

    @staticmethod
    def init_gauss_scaled(amp, length, pos, width):
        if abs(amp) > 1:
            raise ValueError("Amplitude cannot be larger than 1.0!")
        return (
            "wave w_1 = {} * gauss({}, {}, {});\n"
            "wave w_2 = {} * gauss({}, {}, {});\n"
        ).format(amp, length, pos, width, amp, length, pos, width)

    @staticmethod
    def close_bracket():
        return "\n}}"


#################################################################
if __name__ == "__main__":
    pass
