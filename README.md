# declare_config

This Python module allows a declarative syntax for defining the contents of a
configuration file. It also enables easy support for features such as default
configuration values, nested configuration settings (and nested defaults), and
various other useful automatic sugars.

## Example:

```
from pathlib import Path

from declare_config import Configuration,
    Setting, \
    configuration_source, \
    enable_nested_settings

@configuration_provider("$MYAPP_CONFIG")
@configuration_provider("./myapp.yaml")
@configuration_provider("~/init/myapp.yaml")
@configuration_provider("~/.myapp.yaml")
@enable_nested_settings
@enable_expanduser
class MyAppSettings(declare_config.Configuration):
    '''Settings for myapp.'''
    homepage = Setting('urls.root')
    api_root = Setting('urls.api_root', '${homepage}/api')
    timeout_ms = Setting('timeout_ms', 5000, int)
    log_file = Setting("log_location", ~/logs/myapp.log", Path)

settings = MyAppSettings.load()

```

The above code defines a configuration file for a sample application. It
defines four locations that will be searched for the configuration file when
`MyAppSettings.load()` is called: first it will check the value of
the environment variable `$MYAPP_CONFIG` for a file location, and then if no
such environment variable is defined it will check the other three file
locations in order for a configuration file. Whenever it finds a valid file
location, it will load the settings from that file.

Because of the `@enable_nested_settings` decorator, settings are allowed to
reference one another (and default definitions are allowed to reference other
settings as well) through the `${setting_name}` syntax. All settings have type
information,and the `@enable_expanduser` decorator ensures that for any
setting declared to be a filesystem path, the `~/` directory will be expanded
to the user's home directory.

Currently only yaml configuration files are supported, though there are plans
to add support for JSON and INI syntaxes.

## Development

Dependencies are managed with `pipenv`. To install dependencies for
development, run `pipenv install --dev` from the project root.

To run tests once with coverage, use `pipenv run pytest` from the project
root. To run tests continuously during development, run `pipenv run ptw`
instead.
