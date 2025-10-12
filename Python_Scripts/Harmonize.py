import flvfx as vfx
from dataclasses import dataclass
import random

script_text = """Sharpend's Harmonizer
Harmonizer with Quantization, Strum functionality & 2 Randomization algorithms.
----------------------------
Voice: Enable/Disable A harmony voice.
Transpose: Transpose Harmony voice by x Semitones.
Velocity Multiplier: Multiplier of harmony voices' velocity.
Strum: Defines time it takes for harmony voices to strum, by division of 1/16th notes.

Key: Key to quantize the harmony notes to.
Scale: Scale to quantize the harmony notes to.

Range Above: Randomization range of harmony note above played note.
Range Below: Randomization range of harmony note below played note.
Random Relative: Enable Randomization based on a range above/below played note.

Min: Randomization minimum threshold for harmony note.
Max: Randomization maximum threshold for harmony note.
Random Min Max: Enable Randomization based on min/max thresholds.
"""

@dataclass(frozen=True)
class Group:
    NAME: str

@dataclass(frozen=True)
class VoiceGroup(Group):
    NAME: str = "Voices"
    VOICE: str = "Voice"
    TRANSPOSE: str = "Transpose"
    VELOCITY_MULTIPLIER: str = "Velocity Multiplier"
    STRUM: str = "Strum"

@dataclass(frozen=True)
class RandomRelativeGroup(Group):
    NAME: str = "Random Relative"
    RANDOM_RANGE_ABOVE: str = "Range Above"
    RANDOM_RANGE_BELOW: str = "Range Below"

@dataclass(frozen=True)
class RandomMinMaxGroup(Group):
    NAME: str = "Random Min Max"
    RANDOM_MIN: str = "Min"
    RANDOM_MAX: str = "Max"

@dataclass(frozen=True)
class QuantizeGroup(Group):
    NAME: str = "Quantize"
    KEY: str = "Key"
    SCALE: str = "Scale"


@dataclass(frozen=True)
class Groups:
    QUANTIZE: QuantizeGroup = QuantizeGroup()
    VOICE: VoiceGroup = VoiceGroup()
    RANDOM_RELATIVE: RandomRelativeGroup = RandomRelativeGroup()
    RANDOM_MIN_MAX: RandomMinMaxGroup = RandomMinMaxGroup()

@dataclass
class Interface:
    GROUPS: Groups = Groups()

    SCALE_MAJOR = "Major"
    SCALE_MINOR = "Minor"
    SCALE_PENTATONIC_MAJOR = "Pentatonic Major"
    SCALE_PENTATONIC_MINOR = "Pentatonic Minor"
    SCALE_HIJAZ = "Hijaz"
    SCALE_CHROMATIC = "Chromatic"


@dataclass(frozen=True)
class Const:
    NUM_OF_VOICES: int = 4
    DEFAULT_TRANSPOSE_VALUES: tuple[int, ...] = (3, 7, 12, -12)
    MIN_GAP = 3 * NUM_OF_VOICES
    STRUM_MAX_LEN: int = vfx.context.PPQ * 4 * 32
    STRUM_RELEASE_MULTIPLIER: int = vfx.context.PPQ / 16

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
            return limit_note(note)
        else:
            i = 1
            while scale[(degree + i) % 12] != 1:
                i += 1
            offset = i
        return limit_note(note + offset)


class BaseVoice(vfx.Voice):
    parent_voice = None
    note_offset: int = 0
    velocity_multiplier = 1
    trigger_count = 0
    release_count = 0
    triggered = False
    released = False

class HarmonyVoice(BaseVoice):
    delay = 0
    repeat = 0

class MainVoice(BaseVoice):
    pass

def get_group_controller_str(group, name = ''):
    """Get group controller string without acquiring value - for static definitions"""
    name = name if name else group.NAME
    return f"{group.NAME}: {name}"

def get_group_controller(group, name = ''):
    return vfx.context.form.getInputValue(get_group_controller_str(group, name))

def set_group_controller(group, value, name = ''):
    """Set group controller value"""
    print(f"str: {get_group_controller_str(group, name)}")
    print(f"value: {value}")
    vfx.context.form.setNormalizedValue(get_group_controller_str(group, name), value)


def limit_note(note: int):
    """Make sure notes are never above 131(B10), or below 0(C0)"""
    return max(0, min(note, 131))


selected = None
random_switches = [
    get_group_controller_str(RandomRelativeGroup),
    get_group_controller_str(RandomMinMaxGroup)
]
prev_state = [0] * len(random_switches)
voiceList: list[HarmonyVoice] = []
quantizer = ScaleQuantize()
prev_above = 1
prev_below = 1
prev_min = 0
prev_max = 0


class RandomService:
    def __init__(self, active_voices: int, incoming_voice: vfx.Voice, key: int, scale: int):
        self.active_voices = active_voices
        self.incoming_voice = incoming_voice
        self.key = key
        self.scale = scale
        self.random_strategy = self._determine_strategy()


    def _determine_strategy(self):
        if get_group_controller(RandomRelativeGroup):
            return self._relative_strategy
        elif get_group_controller(RandomMinMaxGroup):
            return self._min_max_strategy
        else:
            return None

    def _relative_strategy(self):
        random_notes = self._get_random_notes_relative()
        quantized_notes = self._get_quantized_notes(random_notes)
        return quantized_notes

    def _min_max_strategy(self):
        random_notes = self._get_random_notes_min_max()
        quantized_notes = self._get_quantized_notes(random_notes)
        return quantized_notes

    def randomize_notes(self):
        random_notes = self.random_strategy()
        while not self._is_quantized_notes_random_truly_unique(random_notes):
            random_notes = self.random_strategy()
        for voice, random_note in zip([v for v in voiceList if v.parent_voice == self.incoming_voice],
                                      random_notes):
            voice.note = random_note
            print(f"random note = {random_note}")

    def _get_random_notes_min_max(self):
        rand_min = get_group_controller(RandomMinMaxGroup, RandomMinMaxGroup.RANDOM_MIN)
        rand_max = get_group_controller(RandomMinMaxGroup, RandomMinMaxGroup.RANDOM_MAX)
        possible_values = [i for i in range(rand_min, rand_max) if i != int(self.incoming_voice.note)]
        random_notes = random.sample(possible_values, self.active_voices)
        return random_notes

    def _get_random_notes_relative(self):
        random_range_above = get_group_controller(RandomRelativeGroup, RandomRelativeGroup.RANDOM_RANGE_ABOVE)
        random_range_below = get_group_controller(RandomRelativeGroup, RandomRelativeGroup.RANDOM_RANGE_BELOW)
        possible_values = [i for i in range(-1 * random_range_below, random_range_above + 1) if i != 0]
        random_offsets = random.sample(possible_values, self.active_voices)
        random_notes = [int(self.incoming_voice.note) + offset for offset in random_offsets]
        return random_notes

    def _get_quantized_notes(self, random_notes: list) -> list:
        quantized_notes = []
        for rnd_note in random_notes:
            rnd_note = quantizer.quantize_note(rnd_note, key_index=self.key, scale_index=self.scale)
            quantized_notes.append(rnd_note)
        return quantized_notes


    def _is_quantized_notes_random_truly_unique(self, random_notes):
        quantized_notes = list(set(random_notes))
        if len(quantized_notes) < self.active_voices:
            return False
        else:
            return True

class HarmonyVoiceWorker:
    def __init__(self, incoming_voice: vfx.Voice):
        self.incoming_voice = incoming_voice
        self.main_voice : vfx.Voice = None
        self.active_voices: int = self._get_active_voices()
        self.is_strum_enabled = True if get_group_controller(VoiceGroup, VoiceGroup.STRUM) else False
        self.is_random_enabled = True if get_group_controller(RandomRelativeGroup) or get_group_controller(RandomMinMaxGroup) else False
        self.key = get_group_controller(QuantizeGroup, QuantizeGroup.KEY)
        self.scale = get_group_controller(QuantizeGroup, QuantizeGroup.SCALE)
        self.velocity_multiplier = get_group_controller(VoiceGroup, VoiceGroup.VELOCITY_MULTIPLIER)
        self.strum_delay = get_group_controller(VoiceGroup, VoiceGroup.STRUM)
        self.random_service = RandomService(active_voices=self.active_voices,
                                            incoming_voice=self.incoming_voice,
                                            key=self.key, scale=self.scale)

    def acquire_voices(self):
        self.main_voice = MainVoice()
        self.main_voice.copyFrom(self.incoming_voice)
        self.main_voice.parent_voice = self.incoming_voice
        for i in range(1, self.active_voices + 1):
            new_voice = HarmonyVoice()
            new_voice.copyFrom(self.incoming_voice)
            new_voice.parent_voice = self.incoming_voice
            new_voice.velocity *= self.velocity_multiplier
            if not self.is_random_enabled:
                new_voice.note_offset = get_group_controller(VoiceGroup, f"{VoiceGroup.TRANSPOSE} {i}")
                new_voice.note += new_voice.note_offset
                new_voice.note = quantizer.quantize_note(new_voice.note, key_index=self.key, scale_index=self.scale)
                print(f"NEW NOTE: {new_voice.note}")
            if self.is_strum_enabled:
                new_voice.repeat = i
                new_voice.delay = self.strum_delay
                new_voice.trigger_count = new_voice.repeat * Const.STRUM_RELEASE_MULTIPLIER * new_voice.delay + 1
                new_voice.release_count = new_voice.trigger_count + Const.STRUM_MAX_LEN # Release after being triggered + after MAX LEN at most
            voiceList.append(new_voice)

        if self.active_voices and self.is_random_enabled:
            self.random_service.randomize_notes()

    def trigger_voices(self):
        self.acquire_voices()
        self.main_voice.trigger()
        if not self.is_strum_enabled:
            for voice in [v for v in voiceList if v.parent_voice == self.incoming_voice]:
                if not voice.triggered:
                    voice.trigger()
                    voice.triggered = True
                voiceList.remove(voice)

    def _get_active_voices(self):
        self.active_voices = 0
        for i in range(1, Const.NUM_OF_VOICES+1):
            if get_group_controller(VoiceGroup,f"{VoiceGroup.VOICE} {i}"):
                self.active_voices += 1
        return self.active_voices


def ui_relative_limits():
    """Get state of relative above & below ranges, ensure there's a set gap between them to prevent
     out of range voice allocation"""
    global prev_above, prev_below
    relative_above = get_group_controller(RandomRelativeGroup, RandomRelativeGroup.RANDOM_RANGE_ABOVE)
    relative_below = get_group_controller(RandomRelativeGroup, RandomRelativeGroup.RANDOM_RANGE_BELOW)
    if (relative_above + relative_below) < Const.MIN_GAP:
        if prev_above != relative_above:
            relative_below = abs(Const.MIN_GAP - relative_above)
            set_group_controller(RandomRelativeGroup, relative_below / 48, RandomRelativeGroup.RANDOM_RANGE_BELOW)
        elif prev_below != relative_below:
            relative_above = abs(Const.MIN_GAP - relative_below)
            set_group_controller(RandomRelativeGroup, relative_above / 48, RandomRelativeGroup.RANDOM_RANGE_ABOVE)
    prev_above = relative_above
    prev_below = relative_below


def ui_min_max_limits():
    """Get state of min & max ranges, ensure there's a set gap between them to prevent out of range voice allocation"""
    global prev_min, prev_max
    min_val = get_group_controller(RandomMinMaxGroup, RandomMinMaxGroup.RANDOM_MIN)
    max_val = get_group_controller(RandomMinMaxGroup, RandomMinMaxGroup.RANDOM_MAX)
    if (max_val - min_val) < Const.MIN_GAP:
        if prev_min != min_val:
            max_val = min(min_val + Const.MIN_GAP, 127)
            set_group_controller(RandomMinMaxGroup, max_val / 127, RandomMinMaxGroup.RANDOM_MAX)
            if min_val > (127 - Const.MIN_GAP):
                min_val = 127 - Const.MIN_GAP
                set_group_controller(RandomMinMaxGroup, min_val / 127, RandomMinMaxGroup.RANDOM_MIN)
        elif prev_max != max_val:
            min_val = max(max_val - Const.MIN_GAP, 0)
            set_group_controller(RandomMinMaxGroup, min_val / 127, RandomMinMaxGroup.RANDOM_MIN)
            if max_val < Const.MIN_GAP:
                max_val = Const.MIN_GAP
                set_group_controller(RandomMinMaxGroup, max_val / 127, RandomMinMaxGroup.RANDOM_MAX)
        prev_min = min_val
        prev_max = max_val


def ui_random_state():
    """Get state of random checkboxes, ensure only 1 checkbox can be selected at most"""
    global selected, prev_state
    new_selected = None
    for index, switch in enumerate(random_switches):
        current_value = vfx.context.form.getInputValue(switch)
        if current_value == 1 and prev_state[index] == 0:
            new_selected = index
        prev_state[index] = current_value
    all_off = all(state == 0 for state in prev_state)
    if new_selected is not None:
        selected = new_selected
        for switch in random_switches:
            vfx.context.form.setNormalizedValue(switch, 0)
    if not all_off and selected is not None:
        vfx.context.form.setNormalizedValue(random_switches[selected], 1)


def onTriggerVoice(incomingVoice):
    harmony_voice_worker = HarmonyVoiceWorker(incomingVoice)
    harmony_voice_worker.trigger_voices()

def onReleaseVoice(incomingVoice):
    for live_voice in vfx.context.voices:
        if live_voice.parent_voice == incomingVoice:
            if isinstance(live_voice, MainVoice):
                live_voice.release()
                live_voice.released = True
            if isinstance(live_voice, HarmonyVoice):
                if live_voice.repeat == 0: # If not strummed, release immediately
                    live_voice.release()
                    live_voice.released = True

    harm_voices = [v for v in voiceList if v.parent_voice == incomingVoice]
    for harm_voice in harm_voices: # Live Harmony Voice is strummed, release it in strum order
        harm_voice.release_count = harm_voice.repeat * Const.STRUM_RELEASE_MULTIPLIER * harm_voice.delay + 1


def onTick():
    ui_random_state()

    ui_min_max_limits()

    ui_relative_limits()

    for voice in voiceList[:]:
        voice.trigger_count -=1
        if voice.trigger_count <= 0 and not voice.triggered:
            voice.trigger()
            voice.triggered = True
        voice.release_count -= 1
        if voice.release_count <= 0 and not voice.released:
            if voice is not None:
                voice.release()
                voice.released = True
            voice.released = True
            voiceList.remove(voice)


def createDialog():
    form = vfx.ScriptDialog('', script_text)
    groups = Interface.GROUPS
    form.addGroup(groups.VOICE.NAME)
    for i in range(1, Const.NUM_OF_VOICES + 1):
        form.addInputCheckbox(f'{groups.VOICE.VOICE} {i}', 1, hint=f'Enable Voice {i}')
        form.addInputKnobInt(f'{groups.VOICE.TRANSPOSE} {i}', Const.DEFAULT_TRANSPOSE_VALUES[i-1], -12, 12, hint=f'Transpose Voice {i}')
    form.addInputKnob(groups.VOICE.VELOCITY_MULTIPLIER, 0.5, 0, 2, hint='Voice Velocity Multiplier')
    form.addInputKnobInt(groups.VOICE.STRUM, 0, 0, 16, hint='Strum Timing')
    form.endGroup()


    form.addGroup(groups.QUANTIZE.NAME)
    form.AddInputCombo(groups.QUANTIZE.KEY, quantizer.key_list_interface, 0, hint='Quantize to Key')
    form.AddInputCombo(groups.QUANTIZE.SCALE, quantizer.scale_list_interface, 2, hint='Quantize to Scale')
    form.endGroup()

    form.addGroup(groups.RANDOM_RELATIVE.NAME)
    form.addInputKnobInt(groups.RANDOM_RELATIVE.RANDOM_RANGE_ABOVE, 12, 1, 48, hint=f'Random Range for Harmony Above')
    form.addInputKnobInt(groups.RANDOM_RELATIVE.RANDOM_RANGE_BELOW, 12, 1, 48, hint=f'Random Range for Harmony Below')
    form.addInputCheckbox(groups.RANDOM_RELATIVE.NAME, 0, hint='Enable Relative Harmony Randomization')
    form.endGroup()

    form.addGroup(groups.RANDOM_MIN_MAX.NAME)
    form.addInputKnobInt(groups.RANDOM_MIN_MAX.RANDOM_MIN, 49, 0, 126, hint=f'Random Min Limit for Harmony')
    form.addInputKnobInt(groups.RANDOM_MIN_MAX.RANDOM_MAX, 89, 0, 127, hint=f'Random Max Limit for Harmony')
    form.addInputCheckbox(groups.RANDOM_MIN_MAX.NAME, 0, hint='Enable Min/Max Harmony Randomization')
    form.endGroup()
    return form
