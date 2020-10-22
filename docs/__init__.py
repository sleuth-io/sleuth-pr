"""
Basic example of a Mkdocs-macros module
"""

import math


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - variables: the dictionary that contains the environment variables
    - macro: a decorator function, to declare a macro.
    """
    import os
    os.environ["DJANGO_SETTINGS_MODULE"] = "app.settings.test"
    import django; django.setup()

    from sleuthpr import registry

    env.variables["rule_triggers"] = registry.get_all_trigger_types()
    env.variables["rule_operators"] = registry.get_all_operators()
    env.variables["rule_variables"] = registry.get_all_condition_variable_types()
    env.variables["rule_actions"] = registry.get_all_action_types()
