#!/bin/env python3
import argparse
import copy
import yaml


DESCRIPTION = """\
Reads a template for an i3 configuration file and dynamically edits it based on a configuration
file.

Reads the input file from stdin and outputs the config to stdout.\
"""

# Args
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    '-c',
    '--config-file',
    help="A configuration file.",
    type=argparse.FileType("r"),
    required=True
)


# Classes
class CommandSpec:
    """Represents the specifications for an i3 mode command"""

    def __init__(self, shortcut, template_args):
        self._shortcut = shortcut
        self._template_args = template_args

    def render(self, template):
        out = f"bindsym {self._shortcut} {template}; mode \"default\""
        out = out.format(*self._template_args)
        return out

    @classmethod
    def from_dct(cls, dct):
        """ Initializes from a dictionary """
        cls._ensure_valid_initialization_dct(dct)
        new_dct = cls._standardize_dct(dct)
        return cls(**new_dct)

    @classmethod
    def _ensure_valid_initialization_dct(cls, dct):
        """ Ensures the dct is valid for constructing a CommandSpec """

        if "shortcut" not in dct:
            msg = "Missing shortcut"
            raise RuntimeError(msg)

        if "command" not in dct and "template_args" not in dct:
            msg = "Either command or template_args must be given!"
            raise RuntimeError(msg)

        if "command" in dct and "template_args" in dct:
            msg = "Can not handle both command and template_args"
            raise RuntimeError(msg)

    @classmethod
    def _standardize_dct(cls, dct):
        """ Standardizes the API for creating a new cls from dct """
        new_dct = copy.deepcopy(dct)

        if "command" in new_dct:
            command = new_dct.pop("command")
            new_dct["template_args"] = [command]

        return new_dct


class ModeSpec:
    """Represents the specifications for an i3 mode."""

    REQUIRED_PARAMS = ["name", "commands"]

    def __init__(self, name, command_template, commands):
        self._name = name
        self._command_template = command_template
        self._commands = commands

    def render(self):
        """ Renders the mode as a string """
        out = 'mode "$mode_' + self._name + '" {\n'
        for command in self._commands:
            out += '   ' + command.render(self._command_template) + "\n"
        out += '   bindsym Escape mode "default"\n'
        out += '}'
        return out

    @classmethod
    def from_dct(cls, dct):
        """ Initializes from a dictionary. """
        cls._ensure_valid_initialization_dct(dct)
        new_dct = cls._standardize_dct(dct)
        new_dct["commands"] = [CommandSpec.from_dct(x) for x in new_dct["commands"]]
        return cls(**new_dct)

    @classmethod
    def _standardize_dct(cls, dct):
        """ Standardizes the configuration dct (returning a copy) """
        new_dct = copy.deepcopy(dct)

        if "command_prefix" not in new_dct and "command_template" not in new_dct:
            new_dct["command_prefix"] = ""

        if "command_prefix" in new_dct:
            command_prefix = new_dct.pop('command_prefix')
            new_dct["command_template"] = command_prefix + "{}"

        return new_dct

    @classmethod
    def _ensure_valid_initialization_dct(cls, dct):
        """ Ensures that a given dct is valid for initialization """

        if "command_template" in dct and "command_prefix" in dct:
            msg = "Can not define command_template and command_prefix together"
            raise RuntimeError(msg)

        if "command_template" not in dct and "command_prefix" not in dct:
            msg = ("At least one of command_template or command_prefix must "
                   "be supplied!")
            raise RuntimeError(msg)

        for x in cls.REQUIRED_PARAMS:
            if x not in dct:
                msg = f"Missing parameter: {x}"
                raise RuntimeError(x)


# Script
if __name__ == "__main__":
    args = parser.parse_args()
    config = yaml.safe_load(args.config_file)
    for raw_mode in config['modes']:
        mode = ModeSpec.from_dct(raw_mode)
        print(mode.render())
