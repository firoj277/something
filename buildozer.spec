[app]
title = Live Captions
package.name = livecaptions
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy>=2.1.0,android
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.1.0
fullscreen = 1
android.api = 34
android.minapi = 21
android.ndk = 25b
android.sdk = 34
# android.gradle_dependencies = com.google.android.gms:play-services-speech:20.0.0
android.permissions = RECORD_AUDIO,INTERNET
# android.overlay_permission = 1

[buildozer]
log_level = 2
warn_on_root = 0
