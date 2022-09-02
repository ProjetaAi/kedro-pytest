# kedro-pytest

Helps you testing `Kedro` plugins with `pytest`.

```python
from kedro_pytest import TestKedro

def test_count_cli(tkedro: TestKedro):
    tkedro.new('project')
    # ^ creates a new project in a temporary directory
    tkedro.create_pipeline('pipe')
    # ^ ceates a pipeline and two csv entries in catalog by default
    tkedro.update_yml('conf/base/catalog.yml',
        {'new_dset': {'type': 'pandas.JSONDataSet', 'filepath': 'a.json'}})
    # ^ adds a new dataset to the catalog
    result = tkedro.cli(['count', 'catalog'], ['--type', 'pandas.CSVDataSet'])
    # ^ returns a click.testing.Result object
    assert int(result.output) == 2
    tkedro.stop()
    # ^ cleans the temporary directory (only required for doctests)

def test_helloworld_hook(tkedro: TestKedro):
    with tkedro.new('project') as tk:
      tk.create_pipeline('pipe')
      assert 'Hello world!' in tk.run('pipe').output
```

This plugin focuses on generating minimal `Kedro` structures, such as small
pipelines, and a small project, in order to simplify testing of `Kedro` plugins
in a real `Kedro` environment. Also, to make it safe for testing, the plugin
relies on [pytest-tmpfs](https://github.com/nickolasrm/pytest-tmpfs) to create a temporary filesystem for the project.

## Install

For installing this package, just type the code below in your terminal: 

```
pip install kedro-pytest
```

## Usage

### As a fixture

You can use the `KedroPytest` as a fixture by passing tkedro as an argument of your test function.

```python
from kedro_pytest import TestKedro

def test_fixture(tkedro: TestKedro):
    ...
```

### In doctests

You can always use fixtures in doctests. To do so, you have to inject it into
the doctest namespace in the `conftest` file.

```python
# conftest.py
@pytest.fixture(autouse=True)
def add_to_doctests(doctest_namespace: dict, tkedro: TestKedro):
    """Adds the tkedro fixture to the doctest namespace."""
    doctest_namespace["kedro"] = tkedro

# code.py
def function():
  """
  Example:
      >>> kedro.new('project')
      >>> kedro.create_pipeline('pipe')
      >>> kedro.stop()
  """
  ...
```

### Your own instance

If you seek to use this plugin without pointing to `tmp_path` it is possible to create your own instance and manipulate it the way you want.

```python
from kedro_pytest import TestKedro
from pathlib import Path

def test_my_path():
    tkedro = TestKedro(path=Path.cwd())
    ...
```

## Methods

The following table contains all methods that `TestKedro` implements and its descriptions:

| Method | Description | Parameters | Return |
|---|---|---|---|
| `new` | Creates a new project in a temporary directory. | name: str | `TestKedro` |
| `create_pipeline` | Creates a minimal dummy pipeline with two csv entries in catalog by default and a parameter. | name: str, *content: str | ~ |
| `write_yml` | Writes a yaml file in the project. | path: str, content: dict | str: abs path to the file |
| `read_yml` | Reads a yaml file in the project. | path: str | dict: content of the file |
| `update_yml` | Updates a yaml file in the project. Can be nested, it will replace recursively. | path: str, content: dict | str: abs path to the file |
| `cli` | Runs a kedro cli command in the project. | command: list[str], args: list[str] | `click.testing.Result` |
| `run` | Runs a pipeline in the project. | pipeline: str, run_command: list[str] | `click.testing.Result` |
| `stop` | Cleans the temporary directory. | ~ | ~ |

> Note: The create_pipeline method differs from the cli command because it doesn't need to have a downloaded starter to work.

> Warning: cwd switches between temporary and the last cwd when using new and stop methods of TestKedro. A new instance of the fixture is created for each test, so you don't have to worry about it in tests, but in doctests it may be useful. Also, the use of stop can be avoided by using with statements.

## Advanced usage

If the methods mentioned above are not enough for your needs, you can always use the `fs` attribute of the `TestKedro` instance to manipulate the filesystem.

```python
import json

def test_advanced(tkedro: TestKedro):
    tkedro.new('project')
    tkedro.cli(['json', 'catalog'])
    text = tkedro.fs.read_text('conf/base/catalog.json')
    ...
```

## Contributing

Feel free to contribute with this project, just remember to install and use pre-commit and to write unit tests for it.


