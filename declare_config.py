"""Module for defining configuration file items declaratively.



"""
import os
import pathlib

import yaml

#=============================================================================
# Configuration File Base Class
#=============================================================================

class Configuration:
    """Base class for Configuration objects.

    Subclasses can take any of the decorators in this module defined for
    configuration classes and can declare settings using the ConfiguredValue
    descriptor.

    """
    def __init__(self, config_data=None):
        """Constructor.

        @param config_data: The data with which to populate the configuration.

        """
        self._config_data = config_data or {}

    provider = None

    @classmethod
    def load(cls, *args, **kwargs):
        """

        """
        if cls.provider is None:
            raise TypeError(cls.__name__ + " has no provider defined")

        if args or kwargs:
            config_data = load_configuration(*args, **kwargs)
        else:
            config_data = cls.provider()

        if config_data is None:
            raise ValueError("configuration file could not be loaded")

        return cls(config_data)

    def _resolve(self, config_path, default=None):
        path_parts = key.split('.')
        current_path = self._config_data
        for item in path_parts:
            if item not in current_path:
                return None
            current_path = current_path[item]
        else:
            return current_path


#=============================================================================
# Configuration Providers
#=============================================================================

def load_configuration_from_file(file_location, must_exist=False):
    file_location = pathlib.Path(file_location).expanduser()
    if not file_location.exists():
        if must_exist:
            raise ValueError("could not find configuration file at "
                + file_location)
        else:
            return None

    with file_location.open() as stream:
        return yaml.load(stream)


def load_configuration_from_environment_variable(ev_name):
    ev_value = os.getenv(environment_variable_name)
    if ev_value is None:
        return None
    else:
        load_configuration_from_file(ev_value, must_exist=True)


def load_configuration(location):
    """Attempts to load the configuration file as a dictionary from location.

    Returns None if the location cannot be found.

    """
    if location.startswith("$"):
        ev_name = location[1:]
        return load_configuration_from_environment_variable(ev_name)
    else:
        return load_configuration_from_file(location)


def chain_if_result_is_none(func1, func2):
    if func2 is None:
        return func1

    def chained(*args, **kwargs):
        result = func1(*args, **kwargs)
        if result is not None:
            return result
        else:
            return func2(*args, **kwargs)

    return chained


def configuration_provider(location):
    def decorator(configuration_class):
        configuration_class.provider = classmethod(chain_if_result_is_none(
            lambda cls: load_configuration(location),
            configuration_class.provider))

        return configuration_class

    return decorator



#=============================================================================
# Configuration value descriptor
#=============================================================================

class ConfiguredValue:
    def __init__(self, config_path=None, default=None, setting_type=str):
        """Constructor.

        @param config_path: The path in the configuration file to the item.
        @param defult: The default value to use if no setting value is given.
        @param setting_type: A function to be applied to the resulting string
            configuration setting (usually a constructor for a type, e.g.,
            `int` or `pathlib.Path`). Applied after the default has been
            applied.

        """
        if config_path is None and default is None:
            raise ValueError("must provide config_path or default")

        self.config_path = config_path
        self.default = default

        if not callable(setting_type):
            raise ValueError("must provide callable for setting_type")

        self.setting_type = setting_type

        self.preprocessors = []
        self.postprocessors = []

    def register_preprocessor(self, preprocessor):
        """Add a preprocessor function to be applied before the setting_type.

        Preprocessors are callable objects taking the settings object
        instance as the first positional argument and the string configured
        value for this particular setting (and all previously-applied
        preprocessors) as the second. Preprocessors are called in order of
        registration.

        @param preprocessor: The preprocessor function as described above.

        """
        self.preprocessors.append(preprocessor)

    def register_postprocessor(self, postprocessor):
        """Add a postprocessor function to be applied after the setting_type.

        Postprocessors are callable objects taking the settings object
        instance as the first positional argument and the result of calling
        setting_type (and all previously-applied postprocessors) on the
        configured value for this particular setting as the second.
        Postprocessors are called in order of registration.

        @param preprocessor: The preprocessor function as described above.

        """
        self.postprocessors.append(postprocessor)

    def __get__(self, instance, owner):
        """

        @param instance: The instance this object belongs to, or None if this
            object is being referenced from a class context.
        @param owner: The class to which this endpoint belongs.

        """
        if instance is None:
            return self

        configured_value = None
        if self.config_path is not None:
            configured_value = instance.resolve(self.config_path)

        if configured_value is None:
            if self.default is None:
                raise ValueError("missing required config " + self.config_path)
            else:
                configured_value = self.default

        for preprocessor in self.preprocessors:
            configured_value = preprocessor(instance, configured_value)

        configured_value = self.setting_type(configured_value)

        for postprocessor in self.postprocessors:
            configured_value = postprocessor(instance, configured_value)

        return configured_value


#=============================================================================
# Special Decorators
#=============================================================================

def _get_configured_values(config_class):
    for attr_name in dir(config_class):
        attr_value = getattr(config_class, attr_name)
        if isinstance(attr_value, ConfiguredValue):
            yield attr_value


def enable_nested_settings(config_class):
    """Decorator that enables nested settings.

    @param config_class: The decorated class

    """
    substute_nested_settings = lambda settings, setting_value:
        re.sub(r'\$\{(\w+)\}',
            lambda m: str(getattr(instance, m.group(1))),
            str(setting_value))

    for configured_value in _get_configured_values(config_class):
        configured_value.register_preprocessor(_substitute_nested_settings)

    return config_class


def enable_expanduser(config_class):
    """Decorator that calls expanduser for all Path config settings.

    @param config_class: The decorated class

    """
    expand_user = lambda settings, setting_value: settingValue.expanduser()

    for configured_value in _get_configured_values(config_class):
        if issubclass(configured_value.setting_type, pathlib.Path):
            configured_value.register_postprocessor(expanduser)

    return config_class
