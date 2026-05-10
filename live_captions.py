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

_android_available = False
_android_classes = {}

if platform == "android":
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        from android.permissions import request_permissions

        _android_classes["PythonActivity"] = autoclass('org.kivy.android.PythonActivity')
        _android_classes["Intent"] = autoclass('android.content.Intent')
        _android_classes["RecognizerIntent"] = autoclass('android.speech.RecognizerIntent')
        _android_classes["SpeechRecognizer"] = autoclass('android.speech.SpeechRecognizer')
        _android_available = True
    except Exception:
        _android_available = False


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
        lines = self.label.text.split("\n") if self.label.text else []
        lines = [l for l in lines if l]
        lines.append(text)
        if len(lines) > 5:
            lines.pop(0)
        self.label.text = "\n".join(lines)
        self.label.texture_update()
        self.label.height = self.label.texture_size[1]
        self.scroll_y = 0


if _android_available:
    class AndroidSpeechListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']

        def __init__(self, app):
            super().__init__()
            self.app = app

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, params):
            self.app._on_status("Listening for speech...")

        @java_method('(I)V')
        def onBeginningOfSpeech(self):
            pass

        @java_method('(F)V')
        def onRmsChanged(self, rmsdB):
            pass

        @java_method('(F)V')
        def onBufferReceived(self, buffer):
            pass

        @java_method('(I)V')
        def onEndOfSpeech(self):
            pass

        @java_method('(I)V')
        def onError(self, error):
            self.app._on_recognition_error(error)

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            self.app._on_recognition_results(results)

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, partialResults):
            self.app._on_partial_results(partialResults)

        @java_method('(Landroid/os/Bundle;)V')
        def onSegmentResults(self, segmentResults):
            pass


ERROR_DESCRIPTIONS = {
    1: "Network timeout",
    2: "Network error",
    3: "Audio error",
    4: "Server error",
    5: "Client error",
    6: "Speech timeout",
    7: "No match",
    8: "Recognizer busy",
    9: "Insufficient permissions",
}


class LiveCaptionsApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Live Captions"
        self.running = True
        self.speech_recognizer = None
        self.listener = None

    def build(self):
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

        self.current_line = Label(
            text="",
            markup=True,
            color=(0.9, 0.9, 0.9, 1),
            font_size="20sp",
            halign="center",
            valign="middle",
            size_hint_y=0.2,
        )
        self.caption_box.add_widget(self.current_line)

        self.status_label = Label(
            text="[i]Initialising ...[/i]",
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
        if _android_available:
            self._request_permissions()
        elif platform == "android":
            self._on_status("Android classes failed to load")
        else:
            self._on_status("Speech recognition requires Android device")

    def _request_permissions(self):
        self._on_status("Requesting microphone permission...")
        try:
            request_permissions(
                ["android.permission.RECORD_AUDIO"],
                self._on_permissions_result
            )
        except Exception as exc:
            self._on_status(f"Permission error: {exc}")
            self._try_init_anyway()

    def _try_init_anyway(self):
        self._on_status("Initialising speech recognizer...")
        Clock.schedule_once(lambda dt: self._init_speech_recognizer(), 0.5)

    def _on_permissions_result(self, permissions, grant_results):
        if all(grant_results):
            self._init_speech_recognizer()
        else:
            self._on_status("Microphone permission denied - enable in Settings")

    def _init_speech_recognizer(self):
        try:
            sr = _android_classes["SpeechRecognizer"]
            pa = _android_classes["PythonActivity"]
            self.listener = AndroidSpeechListener(self)
            activity = pa.mActivity
            self.speech_recognizer = sr.createSpeechRecognizer(activity)
            self.speech_recognizer.setRecognitionListener(self.listener)
            self._start_listening()
        except Exception as exc:
            self._on_status(f"Speech init error: {exc}")

    def _start_listening(self):
        if not self.running or not self.speech_recognizer:
            return
        try:
            Intent = _android_classes["Intent"]
            RI = _android_classes["RecognizerIntent"]
            intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RI.EXTRA_PARTIAL_RESULTS, True)
            self.speech_recognizer.startListening(intent)
            self._on_status("Listening...")
        except Exception as exc:
            self._on_status(f"Start error: {exc}")

    def _on_recognition_results(self, results):
        sr = _android_classes["SpeechRecognizer"]
        matches = results.getStringArrayList(sr.RESULTS_RECOGNITION)
        if matches and matches.size() > 0:
            text = matches.get(0)
            if text.strip():
                self._show(text)
        Clock.schedule_once(lambda dt: self._start_listening(), 0.1)

    def _on_partial_results(self, partialResults):
        sr = _android_classes["SpeechRecognizer"]
        matches = partialResults.getStringArrayList(sr.RESULTS_RECOGNITION)
        if matches and matches.size() > 0:
            text = matches.get(0)
            self._show_interim(text)

    def _on_recognition_error(self, error):
        msg = ERROR_DESCRIPTIONS.get(error, f"Error code {error}")
        self._on_status(msg)
        if error in (7, 6, 2):
            Clock.schedule_once(lambda dt: self._start_listening(), 0.5)
        elif error == 8:
            Clock.schedule_once(lambda dt: self._start_listening(), 2)

    def _on_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status_label, "text", f"[i]{text}[/i]"))

    def _show(self, text):
        Clock.schedule_once(lambda dt: self.history.add_line(text))

    def _show_interim(self, text):
        Clock.schedule_once(lambda dt: setattr(self.current_line, "text", text))

    def on_stop(self):
        self.running = False
        if self.speech_recognizer:
            self.speech_recognizer.destroy()


if __name__ == "__main__":
    LiveCaptionsApp().run()
