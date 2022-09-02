"""Implementation of the Kedro tester class."""
from __future__ import annotations
from pathlib import Path
from typing import Any, List, Union, cast
from pytest_tmpfs import TmpFs
from kedro import __version__ as kedro_version
from kedro.framework.cli.cli import KedroCLI
from click import Command
from click.testing import CliRunner, Result
import yaml
from flatten_dict import flatten, unflatten


class TestKedro:
    """Creates a Kedro manager for testing real projects using temporary files.

    This class is a wrapper around some of the Kedro commands with defaults to
    make it easier to generate and test Kedro projects with your plugins. If
    you are using `pytest` there exist a fixture named `tkedro` that you can
    use to access an object of this class that is automatically allocated to
    a temporary directory.

    Attributes:
        path (Path): Path to the project.
        fs (TmpFs): Temporary file system manager.
        project (str): Name of the project.
        pipelines (List[str]): List of created pipelines.

    Note:
        If the functions provided by this class are not enough, you can
        always use the `fs` attribute to access the temporary file system
        and create your own files. The `fs` attribute is a `TmpFs` object
        from the `pytest_tmpfs` package.

    Warning:
        This class is not thread-safe. If you are using it in a multi-threaded
        environment, you should create a new instance for each thread.

    Warning:
        The CWD is only changed if you call the `new` method or if you use the
        method provided by `fs`, you must call the `stop` method to restore
        the old CWD and clean the temporary files.
    """

    def __init__(self, path: Path):
        """Initializes the Kedro manager.

        Args:
            path (Path): Path to be used as temporary directory.
        """
        self.path = path
        self.fs = TmpFs(path)

        self._cli = None
        self.project: Union[str, None] = None
        self.pipelines: List[str] = []

    def _create_minimal_project(self):
        self.fs.mkdir('src')
        self.fs.mkdir('conf/local')
        self.fs.mkdir('conf/base')
        self.fs.mkdir('data')

        self.fs.write(
            'pyproject.toml', '\n'.join([
                '[tool.kedro]',
                f'package_name="{self.project}"',
                f'project_name="{self.project}"',
                f'project_version="{kedro_version}"'
            ])
        )

        self.fs.write(f'src/{self.project}/settings.py', '')
        self.fs.touch(f'src/{self.project}/__init__.py')
        self.fs.touch(f'src/{self.project}/__main__.py')
        self.fs.touch(f'src/{self.project}/pipeline_registry.py')

    def _setup_project(self):
        # Changes cwd to the project directory.
        self.fs.tmp_cwd()

    def _init_cli(self):
        """Initializes the CLI."""
        if self._cli is None:
            self._cli = KedroCLI(self.path)

    def new(self, project: str) -> TestKedro:
        """Creates a minimal Kedro project for testing.

        Args:
            project (str): Name of the project.

        Returns:
            str: Name of the project.

        Example:
            >>> name = kedro.new('my_project')
            >>> kedro.fs.tree('.')  # doctest: +ELLIPSIS
            ├── conf
            │   ├── base
            │   └── local
            ├── data
            ├── pyproject.toml
            └── src
                └── my_project
                    ├── __init__.py
                    ├── __main__.py
                    ├── pipeline_registry.py
                    └── settings.py

            >>> kedro.stop()

            Can be used with the `with` statement.

            >>> with kedro.new('my_project') as p:
            ...     kedro.fs.ls('.')
            ['conf', 'data', 'pyproject.toml', 'src']

            >>> kedro.fs.ls('.')
            []
        """
        self.project = project
        self._create_minimal_project()
        self._setup_project()
        return self

    def stop(self):
        """Restores the old test context.

        Example:
            >>> _ = kedro.new('my_project')
            >>> kedro.fs.ls('.')
            ['conf', 'data', 'pyproject.toml', 'src']

            >>> kedro.stop()
            >>> kedro.fs.ls('.')
            []

            Can be used with the `with` statement.

            >>> with kedro.new('my_project') as p:
            ...     kedro.fs.ls('.')
            ['conf', 'data', 'pyproject.toml', 'src']

            >>> kedro.fs.ls('.')
            []
        """
        self.fs.clean()
        self.fs.cwd()
        self.__init__(self.path)

    def _find_command(self, cmd: List[str]) -> Command:
        # Finds the command in the CLI.
        group: Command = self._cli
        for sub in cmd:
            group = group.get_command(None, sub)
            if group is None:
                raise ValueError(f'Unknown command: {cmd}')
        return group

    def _run_command(self, cmd: Command,
                     args: Union[List[str], None]) -> Result:
        # Runs the CLI command
        res = CliRunner().invoke(cmd, args,
                                 obj=cast(KedroCLI, self._cli)._metadata)
        return res

    def cli(self, cmd: List[str], args: List[str] = None) -> Result:
        r"""Runs Kedro CLI commands.

        Args:
            cmd (List[str]): Command to run.
            args (List[str]): Arguments to pass to the command.
                Defaults to None.

        Returns:
            Result (click.testing.Result): The result of the command.

        Example:
            >>> name = kedro.new('my_project')
            >>> res = kedro.cli(['info'])
            >>> print(res.output)  # doctest: +ELLIPSIS
            <BLANKLINE>
             _            _
            | | _____  __| |_ __ ___
            | |/ / _ \/ _` | '__/ _ \
            |   <  __/ (_| | | | (_) |
            |_|\_\___|\__,_|_|  \___/
            v0.18.2
            <BLANKLINE>
            Kedro is a Python framework for
            ...
            <BLANKLINE>

            >>> kedro.cli(['inexistent', 'command'],
            ...           ['asd'])  # doctest: +ELLIPSIS
            Traceback (most recent call last):
            ...
            ValueError: Unknown command: ['inexistent', 'command']

            >>> kedro.stop()
        """
        self._init_cli()
        command = self._find_command(cmd)
        return self._run_command(command, args)

    def _write_registry(self):
        # Writes pipeline registry importing referenced pipes.
        imports = (f'from {self.project}.pipelines import '
                   f'{", ".join(self.pipelines)}')
        pipes = '{' + ', '.join(f'"{pipeline}": {pipeline}.create_pipeline()'
                                for pipeline in self.pipelines) + '}'

        self.fs.write(
            f'src/{self.project}/pipeline_registry.py',
            'from kedro.pipeline import Pipeline',
            imports,
            '',
            'def register_pipelines():',
            f'    return {pipes}',
            ''
        )

    def write_yml(self, path: str, entries: dict) -> str:
        """Writes a YAML file.

        Args:
            path (str): Path to the file.
            entries (dict): Dictionary of entries to write.

        Returns:
            str: Path to the file.

        Example:
            >>> _ = kedro.write_yml('conf/local/kedro.yml', {'a': 'b'})
            >>> kedro.read_yml('conf/local/kedro.yml')
            {'a': 'b'}
        """
        txt = yaml.dump(entries)
        return self.fs.write(path, txt)

    def read_yml(self, path: str) -> dict:
        """Reads a YAML file.

        Args:
            path (str): Path to the file.

        Returns:
            dict: Dictionary of entries read.

        Example:
            >>> _ = kedro.write_yml('conf/local/kedro.yml', {'a': 'b'})
            >>> kedro.read_yml('conf/local/kedro.yml')
            {'a': 'b'}
        """
        txt = self.fs.read(path)
        return yaml.load(txt, Loader=yaml.FullLoader)

    def update_yml(self, path: str, entries: dict) -> str:
        """Adds or overwrites entries to a YAML file.

        Args:
            path (str): Path to the file.
            entries (dict): Dictionary of entries to update.

        Example:
            >>> _ = kedro.write_yml('conf/local/kedro.yml', {'a': 'b'})
            >>> _ = kedro.update_yml('conf/local/kedro.yml',
            ...                      {'a': 'c', 'b': 'd'})
            >>> kedro.read_yml('conf/local/kedro.yml')
            {'a': 'c', 'b': 'd'}

            >>> nested = {'a': {'b': 'd', 'c': 'e'}}
            >>> _ = kedro.write_yml('conf/local/kedro.yml', nested)
            >>> _ = kedro.update_yml('conf/local/kedro.yml', {'a': {'b': 'f'}})
            >>> kedro.read_yml('conf/local/kedro.yml')
            {'a': {'b': 'f', 'c': 'e'}}
        """
        data = self.read_yml(path)

        data = flatten(data)
        entries = flatten(entries)
        data.update(entries)
        data = unflatten(data)

        return self.write_yml(path, data)

    def _create_example_csv(self):
        # creates a simple csv
        self.fs.write('data/input.csv', 'a,b', '1,0', '2,1', '3,2')

    def _create_example_pipeline_catalog(self, pipeline: str):
        # Creates a catalog.
        self.write_yml(
            f'conf/base/catalog/{pipeline}.yml',
            {
                f'{pipeline}-input': {
                    'type': 'pandas.CSVDataSet',
                    'filepath': 'data/input.csv'
                },
                f'{pipeline}-output': {
                    'type': 'pandas.CSVDataSet',
                    'filepath': 'data/output.csv'
                }
            }
        )

    def _create_example_pipeline(self, pipeline: str, *content: str):
        if not content:
            content = (
                'from kedro.pipeline import Pipeline, node',
                '',
                'def add_column(data, add):',
                '    return data.assign(c=data.a + data.b + add)',
                '',
                'def create_pipeline(**kwargs) -> Pipeline:',
                '    return Pipeline([node(func=add_column,',
                f'        inputs=["{pipeline}-input",',
                f'                "params:{pipeline}-param"],',
                f'        outputs="{pipeline}-output")])'
            )
        self.fs.write(f'src/{self.project}/pipelines/{pipeline}.py', *content)

    def _create_example_pipeline_parameters(self, pipeline: str):
        # Creates a parameters.yml file.
        self.write_yml(
            f'conf/base/parameters/{pipeline}.yml',
            {f'{pipeline}-param': 1}
        )

    def create_pipeline(self,
                        pipeline: str = '__default__',
                        *content: str):
        """Creates a pipeline.

        Args:
            pipeline (str): Name of the pipeline. Defaults to '__default__'.
            *content (str): Lines of code to write to the pipeline file.

        Warning:
            You must define the `create_pipeline` function if you want
            overwrite the contents of it.

        Example:
            >>> name = kedro.new('my_project')
            >>> kedro.create_pipeline('my_pipeline')
            >>> kedro.fs.tree('.')  # doctest: +ELLIPSIS
            ├── conf
            │   ├── base
            │   │   ├── catalog
            │   │   │   └── my_pipeline.yml
            │   │   └── parameters
            │   │       └── my_pipeline.yml
            │   └── local
            ├── data
            │   └── input.csv
            ├── pyproject.toml
            └── src
                └── my_project
                    ├── __init__.py
                    ├── __main__.py
                    ├── pipeline_registry.py
                    ├── pipelines
                    │   └── my_pipeline.py
                    └── settings.py

            >>> kedro.fs.cat('src/my_project/pipeline_registry.py')
            from kedro.pipeline import Pipeline
            from my_project.pipelines import my_pipeline
            <BLANKLINE>
            def register_pipelines():
                return {"my_pipeline": my_pipeline.create_pipeline()}
            <BLANKLINE>

            >>> kedro.fs.cat('conf/base/catalog/my_pipeline.yml')
            my_pipeline-input:
              filepath: data/input.csv
              type: pandas.CSVDataSet
            my_pipeline-output:
              filepath: data/output.csv
              type: pandas.CSVDataSet
            <BLANKLINE>

            >>> kedro.fs.cat('src/my_project/pipelines/my_pipeline.py')
            from kedro.pipeline import Pipeline, node
            <BLANKLINE>
            def add_column(data, add):
                return data.assign(c=data.a + data.b + add)
            <BLANKLINE>
            def create_pipeline(**kwargs) -> Pipeline:
                return Pipeline([node(func=add_column,
                    inputs=["my_pipeline-input",
                            "params:my_pipeline-param"],
                    outputs="my_pipeline-output")])

            >>> kedro.fs.cat('conf/base/parameters/my_pipeline.yml')
            my_pipeline-param: 1
            <BLANKLINE>

            >>> kedro.stop()
        """
        if pipeline not in self.pipelines:
            self.pipelines.append(pipeline)
            self._create_example_csv()
            self._create_example_pipeline(pipeline, *content)
            self._create_example_pipeline_catalog(pipeline)
            self._create_example_pipeline_parameters(pipeline)
            self._write_registry()

    def run(self,
            pipeline: str = '__default__',
            run_command: List[str] = ['run'],
            args: List[str] = []) -> Result:
        """Runs the pipeline.

        Args:
            pipeline (str): Name of the pipeline. Defaults to '__default__'.
            run_command (List[str]): Command to run to run the pipeline.
                Defaults to ['pipeline', 'run'].
            args (List[str]): Arguments to pass to the run command, besides
                the pipeline name. Defaults to [].

        Returns:
            click.testing.Result: Result of the run command.

        Example:
            >>> name = kedro.new('my_project')
            >>> kedro.create_pipeline('my_pipeline')
            >>> res = kedro.run('my_pipeline')
            >>> 'INFO     Pipeline execution completed' in res.output
            True

            >>> kedro.stop()
        """
        result = self.cli(run_command, args + ['--pipeline', pipeline])
        return result

    def __enter__(self) -> TestKedro:
        """Starts the Kedro project.

        Returns:
            TestKedro: TestKedro instance.
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Stops the Kedro project.

        Args:
            exc_type (Any): Exception type.
            exc_val (Any): Exception value.
            exc_tb (Any): Exception traceback.
        """
        self.stop()
