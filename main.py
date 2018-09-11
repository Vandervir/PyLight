import pyaudio
import numpy as np
from magichome import MagicHomeApi
import cv2
import time
from screen import grab_screen
import colorsysą

regions = [(130, 130, 260, 260), (130, 760, 260, 890), (900, 480, 1120, 600), (1660, 130, 1780, 260),
           (1660, 760, 1780, 890)]


class ColorControl:
    parts = 10
    CHANNELS = 1
    RATE = 44100
    VERY_LOUD_SOUND_LEVEL = 5
    LOUD_SOUND_LEVEL = 3
    NORMAL_SOUND_LEVEL = 1
    QUIET_SOUND_LEVEL = 0.5
    VERY_QUIET_SOUND_LEVEL = 0.125

    VERY_LOUD_SOUND_RANGE = 0.4
    LOUD_SOUND_RANGE = 0.2
    NORMAL_SOUND_RANGE = 0.015
    QUIET_SOUND_RANGE = 0.005

    def __exit__(self, exc_type, exc_value, traceback):
        self.controller.turn_off()

    def __init__(self):
        self.time_sleep = 0.05
        self.timer = 0

        self.region = (900, 480, 1120, 600)
        self.region = (0, 0, 1920, 1080)
        self.red_diff = 0
        self.green_diff = 0
        self.blue_diff = 0

        self.sound_level = 0.0

        self.previous_color = self._get_new_dominant_color()
        self.next_color = self._get_new_dominant_color()
        self._init_led()
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  output=True,
                                  input=True,
                                  stream_callback=self._audio_callback)
        pass

    def run(self):
        # update colors
        while (True):
            if self._is_time_to_probe():
                print('probe')
                self.do_magic()

            self._update_colors()

            self.stream.start_stream()
            while self.stream.is_active():
                time.sleep(self.time_sleep)
                self.stream.stop_stream()
            # self.stream.close()
        # write color
        pass

    def do_magic(self):
        self.previous_color = self.next_color
        self.next_color = self._get_new_dominant_color()
        self.red_diff = self._split_parts(self.previous_color[0], self.next_color[0])
        self.green_diff = self._split_parts(self.previous_color[1], self.next_color[1])
        self.blue_diff = self._split_parts(self.previous_color[2], self.next_color[2])
        print(self.red_diff, self.green_diff, self.blue_diff, 'sound level {}'.format(self.sound_level))

    def _get_red(self):
        return self.previous_color[0] + (self.red_diff * self.timer)

    def _get_green(self):
        return self.previous_color[1] + (self.green_diff * self.timer)

    def _get_blue(self):
        return self.previous_color[2] + (self.blue_diff * self.timer)

    def _is_any_color_change(self):
        return self.red_diff + self.green_diff + self.blue_diff != 0

    def _get_white1(self):
        return 0

    def _get_white2(self):
        return 0

    def _split_parts(self, start, end):
        length = abs(start - end)

        end_part = int(length / self.parts)

        if start > end:
            return -end_part
        return end_part

    def _get_new_dominant_color(self):
        screen = grab_screen(self.region)
        data = np.reshape(screen, (-1, 3))
        data = np.float32(data)

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        flags = cv2.KMEANS_RANDOM_CENTERS
        compactness, labels, centers = cv2.kmeans(data, 1, None, criteria, 10, flags)

        return centers[0].astype(np.int32)

    def _init_led(self):
        # return
        self.controller = MagicHomeApi('10.10.123.3', 1)
        self.controller.get_status()
        self.controller.turn_on()

    def _update_colors(self):
        if not self._is_any_color_change():
            return
        # print(self._get_red(), self._get_green(), self._get_blue(), self._get_color_brightest(self._get_red(), self._get_green(), self._get_blue()))
        r, g, b = self._change_saturation_with_sound(self._get_red(), self._get_green(), self._get_blue())
        self.controller.update_device(r, g, b, self._get_white1(), self._get_white2())

    def _change_saturation_with_sound(self, r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        r,g,b = colorsys.hsv_to_rgb(h, s * self.sound_level, v)
        print(self.sound_level, abs(int(r)), abs(int(g)), abs(int(b)))
        return abs(int(r)), abs(int(g)), abs(int(b))

    def _get_color_brightest(self, red, green, blue):
        # ((Red value X 299) + (Green value X 587) + (Blue value X 114)) / 1000
        return ((red * 299) + (green * 587) + (blue * 114) / 1000)

    def get_new_colors(self):
        pass

    def _is_time_to_probe(self):
        if self.timer >= self.parts:
            self.timer = 0
            self.do_magic()
        else:
            self.timer += 1

    def _audio_callback(self, in_data, frame_count, time_info, flag):
        global b, a, fulldata, dry_data, frames
        audio_data = np.fromstring(in_data, dtype=np.float32)
        self.sound_level = self._parse_sound(audio_data.max())
        return (audio_data, pyaudio.paContinue)

    def _parse_sound(self, max_value):
        if max_value > self.VERY_LOUD_SOUND_RANGE:
            return self.VERY_LOUD_SOUND_LEVEL
        elif max_value > self.LOUD_SOUND_RANGE:
            return self.LOUD_SOUND_LEVEL
        elif max_value > self.NORMAL_SOUND_RANGE:
            return self.NORMAL_SOUND_LEVEL
        elif max_value > self.QUIET_SOUND_RANGE:
            return self.QUIET_SOUND_LEVEL
        else:
            return self.VERY_QUIET_SOUND_LEVEL


cc = ColorControl()
cc.run()
