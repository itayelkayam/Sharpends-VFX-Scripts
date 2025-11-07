import flvfx as vfx
import random
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PitchGroup:
    NAME: str = "Pitch"
    PITCH_SEMITONES: str = "Transpose Semi"
    PITCH_OCTAVE: str = "Transpose Oct"


@dataclass(frozen=True)
class VelocityRandomGroup:
    NAME: str = "Velocity Randomization"
    ENABLE_RANDOMIZATION: str = "Enable"
    RANDOMIZE_RELATIVE_PERCENT: str = "Relative %"
    RANDOMIZE_RELATIVE_OFFSET: str = "Relative +/-"
    RANDOMIZE_ABSOLUTE: str = "Absolute"
    RANDOMIZATION_MODE: str = "Mode"
    RANDOMIZATION_MODE_OPTIONS = [
        RANDOMIZE_ABSOLUTE,
        RANDOMIZE_RELATIVE_PERCENT,
        RANDOMIZE_RELATIVE_OFFSET
    ]
    RANDOM_RELATIVE_ABOVE: str = "Relative Above"
    RANDOM_RELATIVE_BELOW: str = "Relative Below"


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


script_text = f"""Sharpend's KeyMod
Modify Velocity & Note offset without MIDI keyboard menu diving
New in v1.1: 2 Relative Velocity Randomization Modes
----------------------------
{PitchGroup.PITCH_SEMITONES}: Note Pitch offset in Semitones.
{PitchGroup.PITCH_OCTAVE}: Note Pitch offset in Octaves.

{VelocityRandomGroup.ENABLE_RANDOMIZATION}: Enable Velocity Randomization. 
{VelocityRandomGroup.RANDOMIZATION_MODE}: Velocity Randomization Mode: {VelocityRandomGroup.RANDOMIZATION_MODE_OPTIONS}.
{VelocityRandomGroup.RANDOM_RELATIVE_ABOVE}: Random Range for Velocity Above played Velocity.
{VelocityRandomGroup.RANDOM_RELATIVE_BELOW}: Random Range for Velocity Below played Velocity.

{VelocityMultOffsetGroup.VELOCITY_MULTIPLIER}: Velocity Multiplier.
{VelocityMultOffsetGroup.VELOCITY_BASE}: Velocity Base Offset.

{VelocityThresholdGroup.VELOCITY_MIN}: Velocity Minimum.
{VelocityThresholdGroup.VELOCITY_MAX}: Velocity Maximum.
"""


def get_group_controller_str(group, name=''):
    """Get group controller string without acquiring value - for static definitions"""
    name = name if name else group.NAME
    return f"{group.NAME}: {name}"


def get_group_controller(group, name=''):
    return vfx.context.form.getInputValue(get_group_controller_str(group, name))


class RandomService:
    def __init__(self, velocity, min_velocity, max_velocity):
        self._velocity = velocity
        self._min_velocity = min_velocity
        self._max_velocity = max_velocity
        self._randomization_type = self._get_randomization_type()
        self._random_strategy = self._determine_strategy()

    def _get_randomization_type(self):
        random_mode_idx = get_group_controller(
            group=VelocityRandomGroup,
            name=Interface.VELOCITY_RANDOM_GROUP.RANDOMIZATION_MODE)
        self._randomization_type = Interface.VELOCITY_RANDOM_GROUP.RANDOMIZATION_MODE_OPTIONS[random_mode_idx]
        print(self._randomization_type)
        return self._randomization_type

    def _determine_strategy(self):
        if self._randomization_type == Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_ABSOLUTE:
            return self._randomize_absolute
        elif self._randomization_type in [
            Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE_PERCENT,
            Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE_OFFSET]:
            return self._randomize_relative
        else:
            raise KeyError('Non existing relative random range!')

    def randomize_velocity(self):
        self._random_strategy()
        return self._velocity

    def _randomize_absolute(self):
        self._velocity = random.uniform(self._min_velocity, self._max_velocity)

    @staticmethod
    def _get_relative_direction(above, below):
        go_above = True
        if above > 0 and below > 0:  # both ranges are enabled
            go_above = random.choice([True, False])  # choose whether to go above or below played velocity
        else:  # only 1 range is enabled
            if above > 0:
                go_above = True
            elif below > 0:
                go_above = False
        return go_above

    def _randomize_relative_percent(self, is_dir_above: bool, above, below):
        if is_dir_above:
            multiplier = 1 + above
        else:
            multiplier = 1 - below
        self._velocity = self._velocity * multiplier

    def _randomize_relative_offset(self, is_dir_above: bool, above, below):
        if is_dir_above:
            offset = above
        else:
            offset = below * -1
        self._velocity = self._velocity + offset

    def _randomize_relative(self):
        below_input = get_group_controller(group=VelocityRandomGroup,
                                           name=Interface.VELOCITY_RANDOM_GROUP.RANDOM_RELATIVE_BELOW) / 100
        above_input = get_group_controller(group=VelocityRandomGroup,
                                           name=Interface.VELOCITY_RANDOM_GROUP.RANDOM_RELATIVE_ABOVE) / 100
        below = random.uniform(0, below_input)
        above = random.uniform(0, above_input)
        is_dir_above = self._get_relative_direction(above, below)

        if self._randomization_type == Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE_PERCENT:
            self._randomize_relative_percent(is_dir_above, above, below)
        elif self._randomization_type == Interface.VELOCITY_RANDOM_GROUP.RANDOMIZE_RELATIVE_OFFSET:
            self._randomize_relative_offset(is_dir_above, above, below)
        else:
            raise KeyError('Non existing relative random range!')


class VelocityMod:
    def __init__(self, velocity):
        self.velocity = velocity
        self.min_velocity = self.get_min()
        self.max_velocity = self.get_max()
        self.base_velocity = self.get_base()
        self.multiplier_velocity = self.get_multiplier()
        self.is_randomization_enabled = self.get_is_randomization_enabled()
        self.random_service = RandomService(velocity=self.velocity,
                                            min_velocity=self.min_velocity, max_velocity=self.max_velocity)

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

    def get_is_randomization_enabled(self):
        self.is_randomization_enabled = bool(get_group_controller(
            group=VelocityRandomGroup,
            name=Interface.VELOCITY_RANDOM_GROUP.ENABLE_RANDOMIZATION))
        return self.is_randomization_enabled

    def randomize_velocity(self):
        self.velocity = self.random_service.randomize_velocity()

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

    if mod.is_randomization_enabled:
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
    for v in vfx.context.voices:
        v.copyFrom(v.parent_voice)
        v.note = v.modified_note
        v.velocity = v.modified_velocity


def onReleaseVoice(incomingVoice):
    for v in vfx.context.voices:
        if v.parent_voice == incomingVoice:
            v.release()


def createDialog():
    form = vfx.ScriptDialog("Sharpend's KeyMod", script_text)
    form.addGroup(Interface.PITCH_GROUP.NAME)
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_SEMITONES, 0, -12, 12, hint='Pitch offset in semitones')
    form.addInputKnobInt(Interface.PITCH_GROUP.PITCH_OCTAVE, 0, -4, 4, hint='Pitch offset in Octaves')
    form.endGroup()

    form.addGroup(Interface.VELOCITY_RANDOM_GROUP.NAME)
    form.addInputCheckbox(Interface.VELOCITY_RANDOM_GROUP.ENABLE_RANDOMIZATION, 0,
                          hint='Enable Velocity Randomization')
    form.addInputCombo(Interface.VELOCITY_RANDOM_GROUP.RANDOMIZATION_MODE,
                       VelocityRandomGroup.RANDOMIZATION_MODE_OPTIONS, 1, 'Velocity Randomization Mode')
    form.addInputKnobInt(Interface.VELOCITY_RANDOM_GROUP.RANDOM_RELATIVE_ABOVE, 0, 0, 100,
                         hint="Random Range for Velocity above played Velocity")
    form.addInputKnobInt(Interface.VELOCITY_RANDOM_GROUP.RANDOM_RELATIVE_BELOW, 0, 0, 100,
                         hint="Random Range for Velocity below played Velocity")
    form.endGroup()

    form.addGroup(Interface.VELOCITY_MULT_OFFSET_GROUP.NAME)
    form.addInputKnob(Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_MULTIPLIER, 1, 0, 2, hint='Velocity Multiplier')
    form.addInputKnob(Interface.VELOCITY_MULT_OFFSET_GROUP.VELOCITY_BASE, 0, -1, 1, hint='Velocity Base Offset')
    form.endGroup()

    form.addGroup(Interface.VELOCITY_THRESHOLD_GROUP.NAME)
    form.addInputKnob(Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MIN, 0, 0, 1, hint='Velocity Minimum')
    form.addInputKnob(Interface.VELOCITY_THRESHOLD_GROUP.VELOCITY_MAX, 1, 0, 1, hint='Velocity Maximum')
    form.endGroup()

    return form
