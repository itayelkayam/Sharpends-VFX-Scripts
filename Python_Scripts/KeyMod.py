import flvfx as vfx
import random
from dataclasses import dataclass

@dataclass(frozen=True)
class PitchGroup:
    NAME: str = "Pitch"
    PITCH_SEMITONES: str = "Transpose Semi"
    PITCH_OCTAVE: str = "Transpose Oct"

@dataclass(frozen=True)
class VelocityGroup:
    NAME: str = "Velocity"
    VELOCITY_MULTIPLIER: str = "Multiplier"
    VELOCITY_BASE: str = "Base Offset"
    VELOCITY_MIN: str = "Min"
    VELOCITY_MAX: str = "Max"
    RANDOMIZE_VELOCITY: str = "Randomize"

@dataclass
class Interface:
    PITCH_GROUP: PitchGroup = PitchGroup()
    VELOCITY_GROUP: VelocityGroup = VelocityGroup()

class VelocityMod:
    def __init__(self, velocity):
        self.velocity = velocity
        self.min_velocity = self.get_min()
        self.max_velocity = self.get_max()
        self.base_velocity = self.get_base()
        self.multiplier_velocity = self.get_multiplier()
        self.is_randomized_velocity = self.get_is_randomized()

    def get_min(self):
        self.min_velocity = get_group_controller(VelocityGroup, Interface.VELOCITY_GROUP.VELOCITY_MIN)
        return self.min_velocity

    def get_max(self):
        self.max_velocity = get_group_controller(VelocityGroup, Interface.VELOCITY_GROUP.VELOCITY_MAX)
        return self.max_velocity

    def get_base(self):
        self.base_velocity = get_group_controller(VelocityGroup, Interface.VELOCITY_GROUP.VELOCITY_BASE)
        return self.base_velocity

    def get_multiplier(self):
        self.multiplier_velocity = get_group_controller(VelocityGroup, Interface.VELOCITY_GROUP.VELOCITY_MULTIPLIER)
        return self.multiplier_velocity

    def get_is_randomized(self):
        self.is_randomized_velocity = bool(get_group_controller(VelocityGroup, Interface.VELOCITY_GROUP.RANDOMIZE_VELOCITY))
        return self.is_randomized_velocity

    def randomize_velocity(self):
        self.velocity = random.uniform(self.min_velocity, self.max_velocity)

    def multiply_velocity(self):
        self.get_multiplier()
        self.velocity = self.velocity * self.multiplier_velocity

    def add_base_to_velocity(self):
        self.get_base()
        self.velocity = self.velocity + self.base_velocity

    def apply_thresholds_to_velocity(self):
        self.get_min()
        self.get_max()
        self.velocity = self.min_velocity if self.velocity < self.min_velocity else self.velocity
        self.velocity = self.max_velocity if self.velocity > self.max_velocity else self.velocity


def modify_velocity(velocity) -> float:
    """Modify velocity according to user params"""
    mod = VelocityMod(velocity)

    if mod.get_is_randomized():
        mod.randomize_velocity()
    mod.multiply_velocity()
    mod.add_base_to_velocity()
    mod.apply_thresholds_to_velocity()

    return mod.velocity


class ModifiedVoice(vfx.Voice):
    def __init__(self, incoming_voice: vfx.Voice):
        self.parent_voice = incoming_voice
        self.copyFrom(self.parent_voice)
        self.offset_semi = get_group_controller(PitchGroup, Interface.PITCH_GROUP.PITCH_SEMITONES)
        self.offset_oct = get_group_controller(PitchGroup, Interface.PITCH_GROUP.PITCH_OCTAVE)
        self.modified_note = self._calc_modified_note()
        self.modified_velocity = modify_velocity(self.velocity)

    def _calc_modified_note(self):
        min_note = 0
        max_note = 127
        note_offset =  self.offset_semi + (self.offset_oct * 12)
        if self.note + note_offset < min_note:
            return min_note
        elif self.note + note_offset > max_note:
            return max_note
        else:
            return self.note + note_offset

def get_group_controller(group, name):
    return vfx.context.form.getInputValue(f"{group.NAME}: {name}")

def onTriggerVoice(incomingVoice):
    # Init the new voice immediately with incomingVoice ensures no race condition between incoming voices
    v = ModifiedVoice(incoming_voice=incomingVoice)
    v.note = v.modified_note
    v.velocity = v.modified_velocity
    v.trigger()


def onTick():
    for v in vfx.context.voices:
        v.copyFrom(v.parent_voice)
        v.note = v.modified_note
        v.velocity = v.modified_velocity


def onReleaseVoice(incomingVoice):
    for v in vfx.context.voices:
        if v.parent_voice == incomingVoice:
            v.release()



def createDialog():
    form = vfx.ScriptDialog("Sharpend's KeyMod", "Sharpend's KeyMod\nModify Velocity & Note offset without MIDI keyboard menu diving")
    form.addGroup(Interface.PITCH_GROUP.NAME)
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_SEMITONES, 0, -12, 12, hint='Pitch offset in semitones')
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_OCTAVE, 0, -4, 4, hint='Pitch offset in Octaves')
    form.endGroup()

    form.addGroup(Interface.VELOCITY_GROUP.NAME)
    form.addInputKnob(Interface.VELOCITY_GROUP.VELOCITY_BASE, 0, -1, 1, hint='Velocity Base')
    form.addInputKnob(Interface.VELOCITY_GROUP.VELOCITY_MULTIPLIER, 1, 0, 2, hint='Velocity Multiplier')
    form.addInputKnob(Interface.VELOCITY_GROUP.VELOCITY_MIN, 0, 0, 1, hint='Velocity Minimum')
    form.addInputKnob(Interface.VELOCITY_GROUP.VELOCITY_MAX, 1, 0, 1, hint='Velocity Maximum')
    form.addInputCheckbox(Interface.VELOCITY_GROUP.RANDOMIZE_VELOCITY, 0, hint='Checkbox to Randomize Velocity')
    form.endGroup()

    return form
