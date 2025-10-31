import flvfx as vfx
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PitchGroup:
    NAME: str = "Pitch"
    PITCH_SEMITONES: str = "Transpose Semi"
    PITCH_OCTAVE: str = "Transpose Oct"


@dataclass(frozen=True)
class VelocityRandomGroup:
    NAME: str = "Velocity Randomization"
    RANDOM_PERCENT_ABOVE: str = "% Above"
    RANDOM_PERCENT_BELOW: str = "% Below"
    RANDOMIZE_RELATIVE: str = "Relative %"
    RANDOMIZE_ABSOLUTE: str = "Absolute"


@dataclass(frozen=True)
class VelocityMultOffsetGroup:
    NAME: str = "Velocity Multiplier & Offset"
    VELOCITY_MULTIPLIER: str = "Multiplier"
    VELOCITY_BASE: str = "Base Offset"


@dataclass(frozen=True)
class VelocityThresholdGroup:
    NAME: str = "Velocity Thresholds"
    VELOCITY_MIN: str = "Min"
    VELOCITY_MAX: str = "Max"


@dataclass
class Interface:
    PITCH_GROUP: PitchGroup = PitchGroup()
    VELOCITY_RANDOM_GROUP: VelocityRandomGroup = VelocityRandomGroup()
    VELOCITY_MULT_OFFSET_GROUP: VelocityMultOffsetGroup = VelocityMultOffsetGroup()
    VELOCITY_THRESHOLD_GROUP: VelocityThresholdGroup = VelocityThresholdGroup()


def get_group_controller_str(group, name=''):
    """Get group controller string without acquiring value - for static definitions"""
    name = name if name else group.NAME
    return f"{group.NAME}: {name}"


def get_group_controller(group, name=''):
    return vfx.context.form.getInputValue(get_group_controller_str(group, name))


selected = None
random_switches = [
    get_group_controller_str(VelocityRandomGroup, name=Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE),
    get_group_controller_str(VelocityRandomGroup, name=Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_ABSOLUTE)
]
prev_state = [0] * len(random_switches)


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


class VelocityMod:
    def __init__(self, velocity):
        self.velocity = velocity
        self.min_velocity = self.get_min()
        self.max_velocity = self.get_max()
        self.base_velocity = self.get_base()
        self.multiplier_velocity = self.get_multiplier()
        self.is_absolute_randomized_velocity: bool = self.get_is_absolute_randomized()
        self.is_relative_randomized_velocity: bool = self.get_is_relative_randomized()

    def get_min(self):
        self.min_velocity = get_group_controller(group=VelocityThresholdGroup,
                                                 name=Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MIN)
        return self.min_velocity

    def get_max(self):
        self.max_velocity = get_group_controller(group=VelocityThresholdGroup,
                                                 name=Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MAX)
        return self.max_velocity

    def get_base(self):
        self.base_velocity = get_group_controller(
            group=VelocityMultOffsetGroup,
            name=Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_BASE)
        return self.base_velocity

    def get_multiplier(self):
        self.multiplier_velocity = get_group_controller(
            group=VelocityMultOffsetGroup,
            name=Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_MULTIPLIER)
        return self.multiplier_velocity

    def get_is_absolute_randomized(self):
        self.is_absolute_randomized_velocity = bool(get_group_controller(
            group=VelocityRandomGroup,
            name=Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_ABSOLUTE))
        return self.is_absolute_randomized_velocity

    def absolute_randomize_velocity(self):
        self.velocity = random.uniform(self.min_velocity, self.max_velocity)

    def get_is_relative_randomized(self):
        self.is_relative_randomized_velocity = bool(get_group_controller(
            group=VelocityRandomGroup,
            name=Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE))
        return self.is_relative_randomized_velocity

    def relative_randomize_velocity(self):
        percent_below_input = get_group_controller(group=VelocityRandomGroup,
                                                   name=Interface.VELOCITY_RANDOM_GROUP.RANDOM_PERCENT_BELOW) / 100
        percent_above_input = get_group_controller(group=VelocityRandomGroup,
                                                   name=Interface.VELOCITY_RANDOM_GROUP.RANDOM_PERCENT_ABOVE) / 100
        percent_below = random.uniform(0, percent_below_input)
        percent_above = random.uniform(0, percent_above_input)

        multiplier = 1
        if percent_above > 0 and percent_below > 0:  # both ranges are enabled
            go_above = random.choice([True, False])  # choose whether to go above or below played velocity
            if go_above:
                multiplier = 1 + percent_above
            else:
                multiplier = 1 - percent_below
        else:  # only 1 range is enabled
            if percent_above > 0:
                multiplier = 1 + percent_above
            elif percent_below > 0:
                multiplier = 1 - percent_below
        self.velocity = self.velocity * multiplier

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

    if mod.is_absolute_randomized_velocity:
        mod.absolute_randomize_velocity()
    elif mod.is_relative_randomized_velocity:
        mod.relative_randomize_velocity()
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
        note_offset = self.offset_semi + (self.offset_oct * 12)
        if self.note + note_offset < min_note:
            return min_note
        elif self.note + note_offset > max_note:
            return max_note
        else:
            return self.note + note_offset


def onTriggerVoice(incomingVoice):
    # Init the new voice immediately with incomingVoice ensures no race condition between incoming voices
    v = ModifiedVoice(incoming_voice=incomingVoice)
    v.note = v.modified_note
    v.velocity = v.modified_velocity
    v.trigger()


def onTick():
    ui_random_state()
    for v in vfx.context.voices:
        v.copyFrom(v.parent_voice)
        v.note = v.modified_note
        v.velocity = v.modified_velocity


def onReleaseVoice(incomingVoice):
    for v in vfx.context.voices:
        if v.parent_voice == incomingVoice:
            v.release()


def createDialog():
    form = vfx.ScriptDialog("Sharpend's KeyMod",
                            "Sharpend's KeyMod\nModify Velocity & Note offset without MIDI keyboard menu diving\n"
                            "New in v1.1: Relative Velocity Randomization")
    form.addGroup(Interface.PITCH_GROUP.NAME)
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_SEMITONES, 0, -12, 12, hint='Pitch offset in semitones')
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_OCTAVE, 0, -4, 4, hint='Pitch offset in Octaves')
    form.endGroup()

    form.addGroup(Interface.VELOCITY_RANDOM_GROUP.NAME)
    form.addInputCheckbox(Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE, 0,
                          hint='Enable Relative Velocity Randomization')
    form.addInputCheckbox(Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_ABSOLUTE, 0,
                          hint='Enable Absolute Velocity Randomization')
    form.addInputKnobInt(Interface.VELOCITY_RANDOM_GROUP.RANDOM_PERCENT_ABOVE, 0, 0, 100,
                         hint="Random Range for Velocity above played Velocity")
    form.addInputKnobInt(Interface.VELOCITY_RANDOM_GROUP.RANDOM_PERCENT_BELOW, 0, 0, 100,
                         hint="Random Range for Velocity below played Velocity")
    form.endGroup()

    form.addGroup(Interface.VELOCITY_MULT_OFFSET_GROUP.NAME)
    form.addInputKnob(Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_MULTIPLIER, 1, 0, 2, hint='Velocity Multiplier')
    form.addInputKnob(Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_BASE, 0, -1, 1, hint='Velocity Base')
    form.endGroup()

    form.addGroup(Interface.VELOCITY_THRESHOLD_GROUP.NAME)
    form.addInputKnob(Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MIN, 0, 0, 1, hint='Velocity Minimum')
    form.addInputKnob(Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MAX, 1, 0, 1, hint='Velocity Maximum')
    form.endGroup()

    return form
