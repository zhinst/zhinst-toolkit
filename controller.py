






class Controller:
    pass





# def set(self, **settings):
#         self.__sequence.set(**settings)

#     def update(self):
#         if self.__sequence.sequence_type == "Simple":
#             if len(self.__waveforms) == 0:
#                 raise Exception("No Waveforms defined!")
#             self.__sequence.set(
#                 buffer_lengths=[w.buffer_length for w in self.__waveforms]
#             )
#         self._upload_program(self.__sequence.get())
#         print("Uploaded sequence program to device!")

#     def add_waveform(self, wave1, wave2):
#         if self.__sequence.sequence_type == "Simple":
#             w = Waveform(wave1, wave2)
#             self.__waveforms.append(w)
#         else:
#             print("AWG Sequence type must be 'Simple' to upload waveforms!")

#     def upload_waveforms(self):
#         self.update()
#         for i, w in enumerate(self.__waveforms):
#             self._upload_waveform(w, i)
#         print(f"Finished uploading {len(self.__waveforms)} waveforms!")
#         self.__waveforms = []



#         self.__awg.set(target="UHFQA", clock_rate=1.8e9)