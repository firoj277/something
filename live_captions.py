"""
Live Captions Overlay for Android
Captures microphone audio and displays real-time captions in a rectangular overlay box.
Built with Kivy — deployable on Android via Buildozer.
"""

import kivy
kivy.require('2.1.0')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform

import speech_recognition as sr
import threading


# ── Rectangular caption box with dark background ──────────────────────────

class CaptionBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.05, 0.05, 0.05, 0.85)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


# ── Scrollable caption history ────────────────────────────────────────────

class CaptionHistory(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True
        self.always_overscroll = False
        self.label = Label(
            text="",
            size_hint_y=None,
            halign="center",
            valign="bottom",
            color=(1, 1, 1, 1),
            font_size="22sp",
            markup=True,
            padding=(12, 8),
        )
        self.add_widget(self.label)

    def add_line(self, text):
        """Append a caption line, keep max 5 lines."""
        lines = self.label.text.split("\n") if self.label.text else []
        lines = [l for l in lines if l]
        lines.append(text)
        if len(lines) > 5:
            lines.pop(0)
        self.label.text = "\n".join(lines)
        self.label.texture_update()
        self.label.height = self.label.texture_size[1]
        self.scroll_y = 0


# ── Main app ──────────────────────────────────────────────────────────────

class LiveCaptionsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Live Captions"
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.running = True

    def build(self):
        # Android: make window fullscreen, always-on-top hint
        if platform == "android":
            Window.softinput_mode = "below_target"

        self.caption_box = CaptionBox(
            orientation="vertical",
            size_hint=(1, None),
            height=240,
            pos_hint={"x": 0, "y": 0},
        )

        self.history = CaptionHistory(size_hint_y=0.8)
        self.caption_box.add_widget(self.history)

        self.status_label = Label(
            text="[i]Initialising …[/i]",
            markup=True,
            color=(0.7, 0.7, 0.7, 1),
            font_size="13sp",
            halign="center",
            valign="middle",
            size_hint_y=0.2,
        )
        self.caption_box.add_widget(self.status_label)

        Window.bind(on_resize=self._on_resize)
        Clock.schedule_once(self._start, 1)
        return self.caption_box

    def _on_resize(self, win, w, h):
        self.caption_box.height = max(120, int(h * 0.28))

    def _start(self, dt):
        self._status("Initialising microphone …")
        threading.Thread(target=self._caption_loop, daemon=True).start()

    def _status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status_label, "text", f"[i]{text}[/i]"))

    def _show(self, text):
        Clock.schedule_once(lambda dt: self.history.add_line(text))

    def _caption_loop(self):
        try:
            with sr.Microphone() as source:
                self._status("Adjusting for ambient noise …")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                self._status("Listening …")

                while self.running:
                    try:
                        audio = self.recognizer.listen(
                            source, timeout=2, phrase_time_limit=5
                        )
                    except sr.WaitTimeoutError:
                        continue

                    try:
                        text = self.recognizer.recognize_google(audio)
                        if text.strip():
                            self._show(text)
                            self._status("Listening …")
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as exc:
                        self._status(f"API error: {exc}")

        except Exception as exc:
            self._status(f"Microphone error: {exc}")

    def on_stop(self):
        self.running = False


if __name__ == "__main__":
    LiveCaptionsApp().run()
