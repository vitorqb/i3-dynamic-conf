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


# Exceptions
class ConfigurationError(BaseException):

    @classmethod
    def missing_template_for_command(cls):
        msg = ("Either `template` must be given for the command or "
               "`command_template` must be given for the mode")
        return cls(msg)

    @classmethod
    def missing_template_args_for_command(cls):
        return cls("`template_args` must be given for all commands.")

    @classmethod
    def missing_required_param(cls, x):
        return cls(f"Missing required parameter: {x}")


# Classes
class CommandSpec:
    """Represents the specifications for an i3 mode command"""

    REQUIRED_PARAMS = ["template", "template_args", "shortcut"]

    def __init__(self, shortcut, template, template_args):
        self._shortcut = shortcut
        self._template_args = template_args
        self._template = template

    def render(self, escape_after=True):
        """
        Renders the command to a string. If escape_after is True, appens a
        escape to the default mode.
        """
        out = f"bindsym {self._shortcut} {self._template}"
        if escape_after is True:
            out += "; mode \"default\""
        out = out.format(*self._template_args)
        return out

    @classmethod
    def from_dct(cls, dct):
        """ Initializes from a dictionary """
        cls._ensure_valid_initialization_dct(dct)
        new_dct = copy.deepcopy(dct)
        return cls(**new_dct)

    @classmethod
    def _ensure_valid_initialization_dct(cls, dct):
        """ Ensures the dct is valid for constructing a CommandSpec """
        for x in cls.REQUIRED_PARAMS:
            if x not in dct:
                raise ConfigurationError.missing_required_param(x)


class ModeSpec:
    """Represents the specifications for an i3 mode."""

    STR_ESCAPE_DEFAULT = '    bindsym Escape mode "default"\n'

    def __init__(self, name, command_template, commands, description=None,
                 shortcut=None, escape_after_each_command=True):
        self._name = name
        self._command_template = command_template
        self._escape_after_each_command = escape_after_each_command
        self._commands = commands
        self._description = description
        self._shortcut = shortcut

    @property
    def name(self):
        return self._name

    def render(self):
        """ Renders the mode as a string """
        out = self._render_set_description(name=self._name,
                                           description=self._description)
        out += 'mode "$mode_' + self._name + '" {\n'
        for command in self._commands:
            out += '    '
            out += command.render(escape_after=self._escape_after_each_command)
            out += "\n"
        out += self.STR_ESCAPE_DEFAULT
        out += '}\n'
        out += self._render_set_shortcut(name=self._name,
                                         shortcut=self._shortcut)
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


class ModeSpecBuilder:
    """ Helper class for building a ModeSpec from a dct """

    REQUIRED_PARAMS = ["name", "commands"]

    @classmethod
    def build(cls, dct):
        """ Initializes a ModeSpec from a config dictionary. """
        cls._ensure_valid_initialization_dct(dct)
        new_dct = cls._standardize_dct(dct)
        new_dct["commands"] = [CommandSpec.from_dct(x) for x in new_dct["commands"]]
        return ModeSpec(**new_dct)

    @classmethod
    def _ensure_valid_initialization_dct(cls, dct):
        """ Ensures that a given dct is valid for initialization """
        for x in cls.REQUIRED_PARAMS:
            if x not in dct:
                raise ConfigurationError.missing_required_param(x)

        for command in dct.get("commands", []):
            if command.get("template_args") is None:
                raise ConfigurationError.missing_template_args_for_command()

    @classmethod
    def _standardize_dct(cls, dct):
        """ Standardizes the configuration dct (returning a copy) """
        result = copy.deepcopy(dct)
        result = cls._ensure_commands_have_template(result)
        return result

    @staticmethod
    def _ensure_commands_have_template(dct):
        out = copy.deepcopy(dct)
        for command in out.get("commands", []):
            if command.get("template") is None:
                if out.get("command_template") is None:
                    raise ConfigurationError.missing_template_for_command()
                command["template"] = out["command_template"]
        return out


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


# Main
def main(config_file, template_file):
    config = yaml.safe_load(config_file)

    modes = [ModeSpecBuilder.build(raw_mode)
             for raw_mode in config.pop('modes', [])]
    vars = [VarSpec.from_dct(raw_var) for raw_var in config.pop('vars', [])]
    raw_i3_config_template = get_str_from_file(template_file)

    i3_config_template = I3ConfigTemplate(raw_i3_config_template)

    return i3_config_template.render(modes, vars)


if __name__ == "__main__":
    args = parser.parse_args()
    result = main(args.config_file, args.template)
    print(result)
