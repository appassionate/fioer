import os
import subprocess
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from .log import get_logger
from .wrapper import FioWrapper
from .input import FioInput
from .utils import process_json_timestamp
from .visualize import FioView

# TODO: job.status: init, created, running, done

logger = get_logger(__name__)


class JobBase(BaseModel):

    JOB_TYPE: str = "base"

    work_path: str
    # TODO:refactor executable later
    executable: str
    # input:

    status: str = "init"

    def write_input(self):
        raise NotImplementedError('run method is not implemented in base')

    def run():
        raise NotImplementedError('run method is not implemented in base')

    def get_file_directory(self, filename):
        return Path(self.work_path).joinpath(filename).absolute()

    # serialize from file related

    def _dump_workpath(self):

        _dict = self.dict()
        with open(Path(self.work_path) / ".fioer_info.json", 'w') as f:
            json.dump(_dict, f, indent=2)

    def _load_workpath(self):
        # it will not be a classmethod, for init state will occurs a recursion prob
        with open(Path(self.work_path) / ".fioer_info.json", 'r') as f:
            _data = json.load(f)
        # using pydantic method to update data to the object
        # TODO: need refactor
        super().__init__(**_data)
        
    
    def _create_scheme(self):
        
        # try to find existing job info to reload
        if Path(self.work_path).exists():
            try:
                self._load_workpath()
                logger.warning(
                    "job info exists, reloaded, if u want create a new job, clean the work_path")
            except:
                logger.warning("job info corrupted, reinit")
                Path(self.work_path).mkdir(parents=True, exist_ok=True)
                self._dump_workpath()

        else:
            Path(self.work_path).mkdir(parents=True, exist_ok=False)
            self._dump_workpath()
        


class FioTask(JobBase):

    JOB_TYPE: str = "fio"
    executable: str = "fio"

    input: FioInput = FioInput()
    view: FioView = None

    cli_params: Optional[dict] = {}

    def __repr__(self):
        return f"FioTask(work_path={self.work_path}, status={self.status}, exec={self.executable}, cli_params={self.cli_params})"

    
    def __init__(self, work_path, input_dict={}, **kwargs):
        """create a fio task
        Args:
            work_path (_type_): task work path
            input_dict (dict, optional): fio input dict(dict type from ini(.fio) type) Defaults to {}.
        """
        
        _work_path = str(Path(work_path).absolute())
        super().__init__(work_path=_work_path, **kwargs)  # pydantic init method

        # TODO: refactor input
        self.input.content = input_dict
        self.view = FioView()
        self.view._load_job_info(self)

        self._create_scheme()

    def write_input(self):

        self.status = "created"
        self._dump_workpath()

        # create work_dir if not exists
        with open(Path(self.work_path) / "input.fio", 'w') as f:
            f.write(self.input.render_dict())

    def process_output_json(self):
        # parse output.json
        with open(Path(self.work_path) / "output.json", 'r') as f:
            output = f.read()
        parsed = process_json_timestamp(output)
        with open(Path(self.work_path) / "parsed.json", 'w') as f:
            json.dump(parsed, f, indent=2)
    
    def run(self, cli_params:dict=None):
        """run fio task

        Args:
            cli_params (dict, optional): param dict listed for fio cli . Defaults to None. example: {"status-interval":"1"} to set the output interval to 1s
        """

        if self.status == "done":
            logger.warning("job already done, if u want to rerun, clean the work_path")
            return
        
        self.status = "running"
        self._dump_workpath()

        self.cli_params = cli_params  # update used cli_params

        if not cli_params:
            cli_params = {}
        # TODO: here still consider the normal log output
        # for it will remained the interrupted log
        format_type = "json"
        if format_type == "json":
            # set output file format: json, need test
            cli_params['output-format'] = 'json'
            cli_params['output'] = 'output.json'

        self.write_input()
        # using fio wrapper to run the job
        logger.info("--run fio task--")
        logger.info("current input.fio:")
        logger.info("\n"+self.input.render_dict())

        fio = FioWrapper(work_path=str(self.work_path),
                         fio_binary=self.executable,
                         config_file="input.fio")
        fio.run(cli_params=cli_params, output_file=None, error_file=None)

        if format_type == "json":
            self.process_output_json()

        logger.info("--fio task done--")

        self.status = "done"
        self._dump_workpath()


# add an abstraction of PurgeTask
# PurgeTask will remove the disk(very dangerous) to the "FOB" state according to the SNIA standard
# using the linux nvme-cli tool to implement the feature
#ref: https://askubuntu.com/questions/1310338/how-to-secure-erase-a-nvme-ssd

#DANGER!!! this task will remove all the data on the nvme(ssd) device

class PurgeTask(JobBase):
    
    
    class PurgeInput(BaseModel):
        content: dict = {} # {"device": "/dev/nvmeXXX"}
    
    JOB_TYPE: str = "purge"
    executable: str = "nvme"

    input: PurgeInput = PurgeInput()
    cli_params: Optional[dict] = {}
    
    def __repr__(self):
        return f"PurgeTask(work_path={self.work_path}, status={self.status}, exec={self.executable}, cli_params={self.cli_params})"


    def __init__(self, work_path, input_dict={}, **kwargs):

        self.work_path = str(Path(work_path).absolute())
        
        self.input.content = input_dict
        self.executable = "nvme"
        
        self._create_scheme()


    def write_input(self):
        
        self.status = "created"
        self._dump_workpath()

        with open(Path(self.work_path) / "input.json", 'w') as f:
            f.write(json.dumps(self.input.content))
    
    def run(self, cli_params=None):
        
        if self.status == "done":
            logger.warning("job already done, if u want to rerun, clean the work_path")
            return
        self.status = "running"
        
        command = f"nvme format {device_name}"
        if not cli_params:
            cli_params = {}
        for key, value in cli_params.items():
            command += f' --{key}={value}'
        self.cli_params = cli_params  # update used cli_params
        self.write_input()
        
        logger.info("--run nvme-cli purge task--")
        logger.info("current input:")
        logger.info("\n"+self.input.content)
        

        
        #wrapper section
        device_name = self.input.content.get("device")

        logger.info(f"current work path: {self.work_path}")
        logger.info(f"executing nvme-cli command: {command}")
        
        # output,error file
        command += f" > output.log"
        command += f" 2> error.log"
        
        with subprocess.Popen(command, shell=True, 
                              cwd=self.work_path, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True) as proc:

            # wrong here, avoid wrong remove            
            proc.stdin.write("N\n")
            proc.stdin.flush()
            
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"fio failed with error:\n{stderr}")
        
        logger.info("--purge task(nvme-cli) done--")
        self.status = "done"
        self._dump_workpath()
        
        pass
