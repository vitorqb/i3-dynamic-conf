import i3_dynamic_conf as sut
from unittest import TestCase, main


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


if __name__ == "__main__":
    main()
