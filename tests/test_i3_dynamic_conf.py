import i3_dynamic_conf as sut
from unittest import TestCase, main

import os


class IntegrationTest(TestCase):

    def test_snapshot_1(self):
        self.maxDiff = None
        test_dir = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(test_dir, "files", "configs",
                                   "config1.yaml")
        template_path = os.path.join(test_dir, "files", "templates",
                                     "template1.conf")
        snapshot_path = os.path.join(test_dir, "files", "snapshots",
                                     "snapshot1.conf")
        with open(config_path) as config_file,\
                open(template_path) as template_file,\
                open(snapshot_path) as snapshot_file:
            self.assertEqual(sut.main(config_file, template_file),
                             sut.get_str_from_file(snapshot_file).strip())


class TestCommandSpec(TestCase):

    def test_render_no_escape_after(self):
        shortcut = "a"
        template_args = ["FOO"]
        command_spec = sut.CommandSpec(shortcut, template_args)

        template = "BAR {}"

        self.assertEqual(command_spec.render(template),
                         "bindsym a BAR FOO; mode \"default\"")

    def test_render_escape_after(self):
        shortcut = "a"
        template_args = ["FOO"]
        command_spec = sut.CommandSpec(shortcut, template_args)

        template = "BAR {}"

        self.assertEqual(command_spec.render(template, escape_after=False),
                         "bindsym a BAR FOO")


class TestI3ConfigTemplate(TestCase):

    def test_substitute_var_simple(self):
        var = sut.VarSpec("foo", "bar")
        original_template = "This is {{VAR_foo}} and more!"
        config = sut.I3ConfigTemplate(original_template)

        result = config._substitute_var(var, original_template)

        self.assertEqual("This is bar and more!", result)

    def test_substitute_var_no_var_returns_identity(self):
        original_template = "foo"
        unknown_var = sut.VarSpec("AAAAA", "BBBBB")
        config = sut.I3ConfigTemplate(original_template)

        result = config._substitute_var(unknown_var, original_template)

        self.assertEqual(original_template, result)


class TestModeSpec(TestCase):

    @staticmethod
    def _default_mode_spec(**kwargs):
        args = {
            "name": "Foo",
            "command_template": "pre {} pos",
            "commands": [sut.CommandSpec("c", ["arg1"])],
            "description": "Desc1",
            **kwargs
        }
        return sut.ModeSpec(**args)

    def test_render_set_description_no_description(self):
        for x in None, "":
            with self.subTest(x=x):
                result = sut.ModeSpec._render_set_description(name="Foo", description=x)
                self.assertEqual("", result)

    def test_render_set_description_with_description(self):
        name = "FOO"
        description = "Some long description"
        expected = f"set $mode_{name} {description}\n"
        result = sut.ModeSpec._render_set_description(name=name, description=description)
        self.assertEqual(expected, result)

    def test_render_set_shortcut_with_shortcut(self):
        name = "Foo"
        shortcut = "$mod+c"
        exp = 'bindsym {} mode "$mode_{}"\n'.format(shortcut, name)
        self.assertEqual(sut.ModeSpec._render_set_shortcut(name=name, shortcut=shortcut), exp)

    def test_render_set_shortcut_no_shortcut(self):
        for x in None, "":
            with self.subTest(x=x):
                self.assertEqual("", sut.ModeSpec._render_set_description("foo", x))

    def test_render_simple(self):
        name = "foo"
        command_template = "before {} after"
        command_shotcut = "s"
        command_template_args = ["arg1"]
        commands = [sut.CommandSpec(command_shotcut, command_template_args)]
        mode_spec = sut.ModeSpec(name, command_template, commands)
        expected = ('mode "$mode_foo" {\n'
                    '    bindsym s before arg1 after; mode "default"\n'
                    '    bindsym Escape mode "default"\n'
                    '}\n')
        self.assertEqual(mode_spec.render(), expected)

    def test_render_with_description(self):
        name = "Bar"
        description = "Baz"
        mode_spec = self._default_mode_spec(name=name, description=description)
        result = mode_spec.render()
        str_set_description = sut.ModeSpec._render_set_description(
            name=name,
            description=description
        )
        self.assertIn(str_set_description, result)

    def test_render_with_shortcut(self):
        shortcut = "$mod+m"
        name = "move"
        exp = sut.ModeSpec._render_set_shortcut(name=name, shortcut=shortcut)
        result = self._default_mode_spec(shortcut=shortcut, name=name).render()
        self.assertTrue(result.endswith(exp))

    def test_mode_init_str(self):
        name = "FOO"
        exp = 'mode "$mode_FOO" {\n'
        self.assertEqual(sut.ModeSpec._gen_mode_init_str(name), exp)


if __name__ == "__main__":
    main()
