import flvfx as vfx  # VFX Script API, for FL <-> Python communication
from dataclasses import dataclass, field, asdict
import random
import math


script_text = """Sharpend's Harp
Harp Crescendo-like simulation by playing fast notes that progress towards target note.
----------------------------
Time Base: Note length to determine the Harp Crescendo base length.
Time Multiplier: Multiplier of Time Base to determine the Harp Crescendo length.
Polyphony Safe: Ensure every note played only starts playing after the previous note finished.
Timing Curve: Affect the timing relationship between notes. 0 - Linear | < 0 Logarithmic | > 0 Exponential.

Harp Direction: Determines the Harp Crescendo direction.
Velocity Multiplier: Velocity Multiplier of Harp notes.
Lower Limit: Lowest MIDI note the harp will start from (0-126)
Higher Limit: Highest MIDI note the harp will start from (1-127)

Key: Key to quantize the Harp notes to.
Scale: Scale to quantize the Harp notes to.
"""




@dataclass(frozen=True)
class QuantizeGroup:
    NAME: str = "Quantize"
    KEY: str = "Key"
    SCALE: str = "Scale"

@dataclass(frozen=True)
class TimeGroup:
    NAME: str = "Time"
    TIME_BASE: str = "Time Base"
    TIME_MULTIPLIER: str = "Time Multiplier"
    POLYPHONY_SAFE: str = "Polyphony Safe"
    TIMING_CURVE: str = "Timing Curve"

@dataclass(frozen=True)
class HarpSettingsGroup:
    NAME: str = "Harp Settings"
    HARP_DIRECTION: str = "Harp Direction"
    HARP_LOW_LIMIT: str = "Lower Limit"
    HARP_HIGH_LIMIT: str = "Higher Limit"
    VELOCITY_MULTIPLIER: str = "Velocity Multiplier"

@dataclass(frozen=True)
class Groups:
    QUANTIZE: QuantizeGroup = QuantizeGroup()
    TIME: TimeGroup = TimeGroup()
    HARP_SETTINGS: HarpSettingsGroup = HarpSettingsGroup()

@dataclass(frozen=True)
class Interface:
    VELOCITY_MULTIPLIER: str = "Velocity Multiplier"
    TIME_BASE: str = "Time Base"
    TIME_MULTIPLIER: str = "Time Multiplier"
    HARP_DIRECTION: str = "Harp Direction"
    HARP_DIRECTION_UP: str = "Upwards"
    HARP_DIRECTION_DOWN: str = "Downwards"
    HARP_LOW_LIMIT: str = "Lower Limit"
    HARP_HIGH_LIMIT: str = "Higher Limit"
    POLYPHONY_SAFE: str = "Polyphony Safe"
    TIMING_CURVE: str = "Timing Curve"
    GROUPS: Groups = Groups()



    SCALE_MAJOR = "Major"
    SCALE_MINOR = "Minor"
    SCALE_PENTATONIC_MAJOR = "Pentatonic Major"
    SCALE_PENTATONIC_MINOR = "Pentatonic Minor"
    SCALE_HIJAZ = "Hijaz"
    SCALE_CHROMATIC = "Chromatic"


@dataclass(frozen=True)
class Const:
    HARP_LEN: int = int(vfx.context.PPQ) // 4
    VOICE_MAX_LEN: int = vfx.context.PPQ * 4 * 32

@dataclass
class TimeDiv:
    key: int
    value: float

class TimeDivisions:
    divisions_dict = {
        "1/32": TimeDiv(key=0, value=1/32),
        "1/16": TimeDiv(key=1, value=1/16),
        "1/8": TimeDiv(key=2, value=1/8),
        "1/4": TimeDiv(key=3, value=1/4),
        "1/2": TimeDiv(key=4, value=1/2),
        "1 Bar": TimeDiv(key=5, value=1),
        "2 Bars": TimeDiv(key=6, value=2),
        "4 Bars": TimeDiv(key=7, value=4),
    }
    divisions_list_interface = [div for div in divisions_dict.keys()]
    divisions_list = [div for div in divisions_dict.values()]


@dataclass
class HarpDir:
    key: str
    value: int


class HarpDirection:
    UP: HarpDir = HarpDir(key=Interface.HARP_DIRECTION_UP, value=0)
    DOWN: HarpDir = HarpDir(key=Interface.HARP_DIRECTION_DOWN, value=1)
    harp_direction_list = [UP, DOWN]
    harp_direction_list_interface = [harp_direction.key for harp_direction in harp_direction_list]

@dataclass
class Key:
    key: str
    value: int


class Keys:
    key_name_list = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    keys_list: list[Key] = [Key(key=key, value=index) for index, key in enumerate(key_name_list)]
    keys_list_interface = [key_obj.key for key_obj in keys_list]


@dataclass
class Scale:
    key: str
    value: list

class Scales:
    scales_dict = {
        Interface.SCALE_MAJOR: Scale(key=Interface.SCALE_MAJOR, value=[1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]),
        Interface.SCALE_MINOR: Scale(key=Interface.SCALE_MINOR, value=[1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0]),
        Interface.SCALE_PENTATONIC_MAJOR: Scale(key=Interface.SCALE_PENTATONIC_MAJOR, value=[1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0]),
        Interface.SCALE_PENTATONIC_MINOR: Scale(key=Interface.SCALE_PENTATONIC_MINOR, value=[1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0]),
        Interface.SCALE_HIJAZ: Scale(key=Interface.SCALE_HIJAZ, value=[1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0]),
        Interface.SCALE_CHROMATIC: Scale(key=Interface.SCALE_CHROMATIC, value=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
    }
    scales_list_interface = [scale.key for scale in scales_dict.values()]
    scales_list = [scale for scale in scales_dict.values()]


class ScaleQuantize:
    def __init__(self):
        self.scales = Scales()
        self.keys = Keys()

        self.key_list = self.keys.keys_list
        self.scale_list = self.scales.scales_list

        self.key_list_interface = self.keys.keys_list_interface
        self.scale_list_interface = self.scales.scales_list_interface

    def quantize_note(self, note, key_index, scale_index):
        note = int(note)
        key_obj = self.key_list[key_index]
        scale_obj = self.scale_list[scale_index]

        tonic = key_obj.value
        scale = scale_obj.value

        degree = (note - tonic) % 12

        if scale[degree] == 1:
            return note
        else:
            i = 1
            while scale[(degree + i) % 12] != 1:
                i += 1
            offset = i
        return note + offset


class BaseVoice(vfx.Voice):
    parent_voice = None
    velocity_multiplier = 1
    trigger_count = 0
    release_count = 0
    triggered = False
    released = False

class MainVoice(BaseVoice):
    pass


class HarpVoice(BaseVoice):
    pass


voiceList: list[BaseVoice] = []
quantizer = ScaleQuantize()

def get_group_controller(group, name):
    return vfx.context.form.getInputValue(f"{group.NAME}: {name}")


class HarpVoiceWorker:
    def __init__(self, incoming_voice: vfx.Voice):
        self.incoming_voice = incoming_voice
        self.main_voice: vfx.Voice = None
        self.key = get_group_controller(Interface.GROUPS.QUANTIZE, QuantizeGroup.KEY)
        self.scale = get_group_controller(Interface.GROUPS.QUANTIZE, QuantizeGroup.SCALE)
        self.velocity_multiplier = get_group_controller(Interface.GROUPS.HARP_SETTINGS, HarpSettingsGroup.VELOCITY_MULTIPLIER)
        self.direction = get_group_controller(Interface.GROUPS.HARP_SETTINGS, HarpSettingsGroup.HARP_DIRECTION)
        self.harp_low_limit = get_group_controller(Interface.GROUPS.HARP_SETTINGS, HarpSettingsGroup.HARP_LOW_LIMIT)
        self.harp_high_limit = get_group_controller(Interface.GROUPS.HARP_SETTINGS, HarpSettingsGroup.HARP_HIGH_LIMIT)
        self.timing_curve = get_group_controller(Interface.GROUPS.TIME, TimeGroup.TIMING_CURVE)

        self.time_base = TimeDivisions.divisions_list[int(get_group_controller(Interface.GROUPS.TIME, TimeGroup.TIME_BASE))].value
        self.time_multiplier = get_group_controller(Interface.GROUPS.TIME, TimeGroup.TIME_MULTIPLIER)
        self.bar_length = vfx.context.PPQ * 4
        self.is_polyphony_safe = get_group_controller(Interface.GROUPS.TIME, TimeGroup.POLYPHONY_SAFE)

    def acquire_voices(self):
        self.main_voice = MainVoice()
        self.main_voice.copyFrom(self.incoming_voice)
        self.main_voice.parent_voice = self.incoming_voice
        note_list = self.get_harp_notes_list_with_direction()
        if not note_list:
            self.main_voice.trigger()
            return
        main_voices_notes = [int(v.note) for v in voiceList if isinstance(v, MainVoice)]
        main_voices_notes.append(int(self.main_voice.note))
        print(f"main voices: {main_voices_notes}")
        unique_note_list = [note for note in note_list if int(note) not in main_voices_notes]
        print(unique_note_list)
        total = len(unique_note_list)
        if not total:
            self.main_voice.trigger()
            return
        fixed_total_duration = self.bar_length * self.time_base * self.time_multiplier
        delays = self.get_delay_list(num_notes=total, max_delay=fixed_total_duration)
        polyphony_releases = [delays[idx + 1] - delays[idx] for idx in range(total)]
        max_release = 0
        note_length = Const.HARP_LEN
        for idx, quantized_note in enumerate(unique_note_list):


            delay = delays[idx]
            release_length = delay + polyphony_releases[idx] if self.is_polyphony_safe else delay + note_length

            new_voice = HarpVoice()
            new_voice.copyFrom(self.main_voice)
            new_voice.parent_voice = self.incoming_voice
            new_voice.velocity *= self.velocity_multiplier
            new_voice.note = quantized_note
            new_voice.trigger_count = delay
            new_voice.release_count = release_length

            max_release = max(max_release, new_voice.release_count)
            voiceList.append(new_voice)
        latest_trigger_not_polyphony_safe = max(delays) + 1
        main_voice_trigger = max_release + 1 if self.is_polyphony_safe else latest_trigger_not_polyphony_safe
        self.main_voice.trigger_count = main_voice_trigger
        self.main_voice.release_count = self.main_voice.trigger_count + Const.VOICE_MAX_LEN
        voiceList.append(self.main_voice)
        print(self.main_voice.__dict__)


    def get_harp_notes_list_with_direction(self):
        note_list = []
        range_end = int(self.main_voice.note)
        if self.direction == HarpDirection.UP.value:
            range_start = self.harp_low_limit
            range_end = range_end if range_end < self.harp_high_limit else self.harp_high_limit
            range_step = 1

        elif self.direction == HarpDirection.DOWN.value:
            range_start = self.harp_high_limit
            range_end = range_end if range_end > self.harp_low_limit else self.harp_low_limit
            range_step = -1

        for note in range(range_start, range_end, range_step):
            quantized_note = quantizer.quantize_note(note, key_index=self.key, scale_index=self.scale)
            note_list.append(quantized_note)
        return note_list

    def get_delay_list(self, num_notes, max_delay):
        values = []
        num_notes += 1
        curve_strength = 8 ** self.timing_curve
        for i in range(num_notes):
            t = i / (num_notes - 1)  # normalized x from 0 to 1

            if curve_strength == 1:
                y = t
            elif curve_strength > 1:
                y = t ** curve_strength  # exponential-style
            else:
                y = 1 - (1 - t) ** (1 / curve_strength)  # logarithmic-style

            values.append(int(round(y * max_delay)))

        return values


def onTriggerVoice(incomingVoice):
    harp_voice_worker = HarpVoiceWorker(incomingVoice)
    harp_voice_worker.acquire_voices()


def onTick():
    for voice in voiceList[:]:
        voice.trigger_count -= 1
        if voice.trigger_count <= 0 and not voice.triggered:
            voice.trigger()
            voice.triggered = True
        voice.release_count -= 1
        if voice.release_count <= 0 and not voice.released:
            if voice is not None:
                voice.release()
                voice.released = True
            voiceList.remove(voice)


def onReleaseVoice(incomingVoice):
    for live_voice in vfx.context.voices:
        if live_voice.parent_voice == incomingVoice:
            live_voice.release()
            live_voice.released = True
            if live_voice in voiceList:
                voiceList.remove(live_voice)
    for voice in voiceList[:]:
        if isinstance(voice, MainVoice) and voice.parent_voice == incomingVoice:
            voice.trigger_count = 0
            voice.release_count = 1

    harm_voices = [v for v in voiceList if v.parent_voice == incomingVoice and not isinstance(v, MainVoice)]
    for harm_voice in harm_voices:
        if not harm_voice.triggered:
            harm_voice.trigger()
            harm_voice.triggered = True
            harm_voice.release()
            harm_voice.released = True
            voiceList.remove(harm_voice)



def createDialog():
    form = vfx.ScriptDialog("Sharpend's Harp", script_text)
    form.addGroup(Interface.GROUPS.TIME.NAME)
    form.addInputCombo(Interface.GROUPS.TIME.TIME_BASE, TimeDivisions.divisions_list_interface, 2, hint='Time Base Division')
    form.addInputKnobInt(Interface.GROUPS.TIME.TIME_MULTIPLIER, 1, 1, 16, hint='Time Multiplier')
    form.addInputCheckbox(Interface.GROUPS.TIME.POLYPHONY_SAFE, 0, hint="Ensure Harp Notes don't Overlap")
    form.addInputKnob(Interface.GROUPS.TIME.TIMING_CURVE, 0, -1, 1, hint='Timing Curve | 0 = Linear | < 0 = Logarithmic | > 0 = Exponential')
    form.endGroup()

    form.addGroup(Interface.GROUPS.HARP_SETTINGS.NAME)
    form.AddInputCombo(Interface.GROUPS.HARP_SETTINGS.HARP_DIRECTION, HarpDirection.harp_direction_list_interface,
                       HarpDirection.UP.value, hint='Harp Direction')
    form.addInputKnob(Interface.GROUPS.HARP_SETTINGS.VELOCITY_MULTIPLIER, 0.5, 0, 2, hint='Voice Velocity Multiplier')
    form.addInputKnobInt(Interface.GROUPS.HARP_SETTINGS.HARP_LOW_LIMIT, 48, 0, 126, hint=f'Low Limit for Harp')
    form.addInputKnobInt(Interface.GROUPS.HARP_SETTINGS.HARP_HIGH_LIMIT, 96, 1, 127, hint=f'High Limit for Harp')
    form.endGroup()

    form.addGroup(Interface.GROUPS.QUANTIZE.NAME)
    form.AddInputCombo(Interface.GROUPS.QUANTIZE.KEY, quantizer.key_list_interface, 0, hint='Quantize to Key')
    form.AddInputCombo(Interface.GROUPS.QUANTIZE.SCALE, quantizer.scale_list_interface, 2, hint='Quantize to Scale')
    form.endGroup()
    return form

