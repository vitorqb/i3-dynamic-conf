#!/bin/env python3
import argparse
import copy
import yaml
import os


DESCRIPTION = """\
Reads a template for an i3 configuration file and dynamically edits it
based on a configuration file and common patterns.\
"""

# Args
parser = argparse.ArgumentParser(description=DESCRIPTION)
parser.add_argument(
    '-c',
    '--config-file',
    help="A configuration file. Defaults to ~/.config/i3-dynamic-conf/config.yaml",
    type=argparse.FileType("r"),
    default=os.path.expanduser("~/.config/i3-dynamic-conf/config.yaml")
)
parser.add_argument(
    '-t',
    '--template',
    help="A i3 config template that will be used for substitution. Defaults to ~/.config/i3-dynamic-conf/template",
    type=argparse.FileType("r"),
    default=os.path.expanduser("~/.config/i3-dynamic-conf/template"),
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
    STR_ESCAPE_DEFAULT = '    bindsym Escape mode "default"\n'

    def __init__(self, name, command_template, commands, description=None, shortcut=None):
        self._name = name
        self._command_template = command_template
        self._commands = commands
        self._description = description
        self._shortcut = shortcut

    @property
    def name(self):
        return self._name

    def render(self):
        """ Renders the mode as a string """
        out = self._render_set_description(name=self._name, description=self._description)
        out += 'mode "$mode_' + self._name + '" {\n'
        for command in self._commands:
            out += '    ' + command.render(self._command_template) + "\n"
        out += self.STR_ESCAPE_DEFAULT
        out += '}\n'
        out += self._render_set_shortcut(name=self._name, shortcut=self._shortcut)
        return out

    @staticmethod
    def _render_set_description(name, description):
        if description == "" or description is None:
            return ""
        return f"set $mode_{name} {description}\n"

    @staticmethod
    def _render_set_shortcut(name, shortcut):
        if shortcut == "" or shortcut is None:
            return ""
        return 'bindsym {} mode "{}"\n'.format(shortcut, f"$mode_{name}")

    @staticmethod
    def _gen_mode_init_str(name):
        return 'mode "$mode_' + name + '" {\n'

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


class I3ConfigTemplate:
    """ Represents the template for the i3 configuration """

    def __init__(self, original_template):
        self._original_template = original_template

    def render(self, modes, vars):
        """ Renders the template into the final config.
        `modes` must be a list of ModeSpec that will be substituted. """
        out = copy.deepcopy(self._original_template)

        for mode in modes:
            out = self._substitute_mode(mode, out)

        for var in vars:
            out = self._substitute_var(var, out)

        return out

    def _substitute_mode(self, mode, template):
        """ Substitutes `mode` into `template`, if found, and returns.
        If not found, returns template as-is."""
        mode_target = "{{MODE_" + mode.name + "}}"
        return template.replace(mode_target, mode.render())

    def _substitute_var(self, var, template):
        """ Substitutes `vars` into `template`, if found, and returns.
        If not found, returns template as-is. """
        var_target = "{{VAR_" + var.name + "}}"
        return template.replace(var_target, var.value)


class VarSpec:
    """ A variable, with a name and a value, that can be substituted """
    def __init__(self, name, value):
        self._name = name
        self._value = value

    @property
    def name(self): return self._name

    @property
    def value(self): return self._value

    @classmethod
    def from_dct(cls, dct):
        """ Initializes VarSpec from a dct """
        return cls(name=dct['name'], value=dct['value'])


# Helper fns
def get_str_from_file(f):
    out = ""
    for line in f:
        out += line
    return out


# Script
if __name__ == "__main__":
    args = parser.parse_args()
    config = yaml.safe_load(args.config_file)

    modes = [ModeSpec.from_dct(raw_mode) for raw_mode in config.pop('modes', [])]
    vars = [VarSpec.from_dct(raw_var) for raw_var in config.pop('vars', [])]
    raw_i3_config_template = get_str_from_file(args.template)

    i3_config_template = I3ConfigTemplate(raw_i3_config_template)

    print(i3_config_template.render(modes, vars))
