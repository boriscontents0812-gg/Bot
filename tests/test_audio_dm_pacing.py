import unittest
import os
import wave
import struct
import audio_generator

class TestAudioDmPacing(unittest.TestCase):
    def test_trim_audio_silence_removes_dead_space(self):
        # Create a synthetic wave with 100ms silence, 200ms tone, 100ms silence
        sr = 44100
        test_file = 'tests/temp_test_vad.wav'
        os.makedirs('tests', exist_ok=True)
        
        silence_100ms = [0] * int(sr * 0.100 * 2)
        # Tone of 500Hz with amplitude 5000
        tone_200ms = []
        for i in range(int(sr * 0.200)):
            val = int(5000 * (1 if (i % 88) < 44 else -1))
            tone_200ms.extend([val, val])
        
        all_samples = silence_100ms + tone_200ms + silence_100ms
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f'<{len(all_samples)}h', *all_samples))
            
        dur_orig = int(round(len(all_samples) // 2 * 1000.0 / sr))
        self.assertEqual(dur_orig, 400)
        
        trimmed_ms = audio_generator.trim_audio_silence(test_file, lead_pad_ms=5, trail_pad_ms=15)
        # 200ms tone + 5ms lead + 15ms trail = ~220ms
        self.assertAlmostEqual(trimmed_ms, 220, delta=15)
        
        # Verify first 15ms has immediate sound onset
        with wave.open(test_file, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        s = struct.unpack(f'<{n*2}h', raw)
        first_15ms = s[:int(sr * 0.015 * 2)]
        peak_onset = max(abs(x) for x in first_15ms)
        self.assertGreater(peak_onset, 1000, "Speech sound must start within 15ms of onset (zero dead space)!")
        
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_zero_dead_space_exact_sync(self):
        sr = 44100
        test_file = 'tests/temp_test_zero_vad.wav'
        os.makedirs('tests', exist_ok=True)
        
        silence_100ms = [0] * int(sr * 0.100 * 2)
        # 500Hz tone for 250ms with amplitude 6000
        tone_250ms = []
        for i in range(int(sr * 0.250)):
            val = int(6000 * (1 if (i % 88) < 44 else -1))
            tone_250ms.extend([val, val])
        
        all_samples = silence_100ms + tone_250ms + silence_100ms
        with wave.open(test_file, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(struct.pack(f'<{len(all_samples)}h', *all_samples))

        trimmed_ms = audio_generator.trim_audio_silence(test_file, lead_pad_ms=0, trail_pad_ms=0)
        self.assertAlmostEqual(trimmed_ms, 250, delta=10)

        # Verify sound onset begins immediately at the start of the trimmed file (within 3ms)
        with wave.open(test_file, 'rb') as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
        s = struct.unpack(f'<{n*2}h', raw)
        first_3ms = s[:int(sr * 0.003 * 2)]
        peak_onset = max(abs(x) for x in first_3ms)
        self.assertGreater(peak_onset, 1000, "Speech sound must start on sample onset (within 3ms)!")

        # Verify trailing silence is trimmed to zero
        last_3ms = s[-int(sr * 0.003 * 2):]
        peak_offset = max(abs(x) for x in last_3ms)
        self.assertGreater(peak_offset, 1000, "Speech sound must end immediately at clip boundary!")

        if os.path.exists(test_file):
            os.remove(test_file)

    def test_concat_wav_zero_gap_perfect_sync(self):
        self.assertEqual(audio_generator.concat_wav_files([], "dummy.wav"), 0)
        
        sr = 44100
        f1 = 'tests/temp_f1.wav'
        f2 = 'tests/temp_f2.wav'
        f_out = 'tests/temp_concat.wav'
        try:
            tone = struct.pack(f'<{int(sr * 0.100 * 2)}h', *([3000] * int(sr * 0.100 * 2)))
            for f in (f1, f2):
                with wave.open(f, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(tone)
            
            dur = audio_generator.concat_wav_files([f1, f2], f_out, pause_ms=0, outro_pause_ms=0)
            self.assertAlmostEqual(dur, 200, delta=5)
            with wave.open(f_out, 'rb') as wf:
                actual_ms = int(round(wf.getnframes() * 1000.0 / wf.getframerate()))
            self.assertEqual(actual_ms, 200)
        finally:
            for f in (f1, f2, f_out, f_out.replace('.wav', '.mp3')):
                if os.path.exists(f):
                    os.remove(f)

if __name__ == '__main__':
    unittest.main()
