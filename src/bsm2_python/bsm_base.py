"""This represents a base model of a BSM model.

It models basic input and output data,
and deals with model-independent parameters.
"""

import csv
import os

import numpy as np

from bsm2_python.evaluation import Evaluation
from bsm2_python.log import logger

path_name = os.path.dirname(__file__)


class BSMBase:
    """Creates a BSMBase object. It is a skeleton class and resembles basic
    Input and output data of the BSM model.
    It is not meant to be used directly.

    Parameters
    ----------
    data_in : np.ndarray(n, 22) | str (optional)
        Influent data. Has to be a 2D array. <br>
        First column is time [d], the rest are 21 components
        (13 ASM1 components, TSS, Q, T and 5 dummy states).
        If a string is provided, it is interpreted as a file name.
        If not provided, the influent data from BSM2 is used. \n
        [SI, SS, XI, XS, XBH, XBA, XP, SO, SNO, SNH, SND, XND, SALK, TSS, Q, TEMP, SD1, SD2, SD3, XD4, XD5]
    timestep : float (optional)
        Timestep for the simulation [d]. <br>
        If not provided, the timestep is set to 1 minute. <br>
        Please note: Due to sensor sensitivity, the timestep should not be larger than 1 minute.
    endtime : float (optional)
        Endtime for the simulation [d]. <br>
        If not provided, the endtime is the last time step in the influent data.
    evaltime : int | np.ndarray(2) | list[float] | tuple[float] (optional)
        Evaluation time for the simulation [d]. <br>
        When passed as an int, it defines the number of last days of the simulation to be evaluated.
        When passed as a 1D np.ndarray or list with two values, it defines
        the start and end time of the evaluation period.
        If not provided, the last 5 days of the simulation will be assessed. \n
        [starttime, self.simtime[-1]]
    data_out : str (optional)
        Path to the output data file. <br>
        If not provided, no output data is saved.
    """

    def __init__(
        self,
        data_in: np.ndarray | str | None = None,
        timestep: float | None = None,
        endtime: float | None = None,
        evaltime: int | np.ndarray | list[float] | tuple[float] | None = None,
        data_out: str | None = None,
    ):
        if data_in is None:
            # dyninfluent from BSM2:
            with open(path_name + '/data/dyninfluent_bsm2.csv', encoding='utf-8-sig') as f:
                self.data_in = np.array(list(csv.reader(f, delimiter=','))).astype(float)
        elif isinstance(data_in, str):
            with open(data_in, encoding='utf-8-sig') as f:
                self.data_in = np.array(list(csv.reader(f, delimiter=','))).astype(float)
        elif isinstance(data_in, np.ndarray):
            self.data_in = data_in.astype(float)
        else:
            raise ValueError('data_in must be a numpy array, a string or None.')

        if isinstance(timestep, int | float):
            self.simtime = np.arange(0, self.data_in[-1, 0], timestep, dtype=float)
            self.timesteps = timestep * np.ones(len(self.simtime) - 1)
        elif timestep is None:
            # calculate difference between each time step in data_in
            self.simtime = self.data_in[:, 0].flatten()
            self.timesteps = np.diff(self.data_in[:, 0], append=(2 * self.data_in[-1, 0] - self.data_in[-2, 0]))
        else:
            err = 'Timestep must be a number or None.\n \
                Please provide a valid timestep.\n'
            raise ValueError(err)

        if endtime is None:
            self.endtime = self.data_in[-1, 0]
        elif isinstance(endtime, int | float):
            if endtime > self.data_in[-1, 0]:
                err = 'Endtime is larger than the last time step in data_in.\n \
                    Please provide a valid endtime.\n Endtime should be given in days.'
                raise ValueError(err)
            self.endtime = endtime
            self.simtime = self.simtime[self.simtime <= endtime].flatten()
        else:
            err = 'Endtime must be a number or None.\n \
                Please provide a valid endtime.\n'
            raise ValueError(err)
        self.data_time = self.data_in[:, 0]

        if isinstance(evaltime, np.ndarray | list | tuple):
            # allow a 1D numpy array or a list/tuple with two float values
            dim_eval = 2
            if len(evaltime) != dim_eval:
                raise ValueError('evaltime must be a 1D numpy array or list with two values.')
            try:
                start, end = map(float, evaltime)
            except Exception as excpt:
                raise ValueError('evaltime values must be numbers.') from excpt
            if start < self.simtime[0] or end > self.simtime[-1]:
                raise ValueError('evaltime must be within the simulation time.')
            self.evaltime = np.array([start, end])
        elif isinstance(evaltime, int):
            # evaluate the last evaltime days of the simulation
            if evaltime > self.simtime[-1]:
                err = 'evaltime is larger than the simulation time.\n \
                    The evaluation time must be within the simulation time.'
                raise ValueError(err)
            if evaltime < 0:
                err = 'evaltime must be a positive number.\n \
                    The evaluation time must be within the simulation time.'
                raise ValueError(err)
            starttime = self.simtime[np.argmin(np.abs(self.simtime - (self.simtime[-1] - evaltime)))]
            self.evaltime = np.array([starttime, self.simtime[-1]])
            self.evaltime = np.array([evaltime, self.simtime[-1]])
        elif evaltime is None:
            # evaluate the last 5 days of the simulation
            last_days = 5
            starttime = self.simtime[np.argmin(np.abs(self.simtime - (self.simtime[-1] - last_days)))]
            self.evaltime = np.array([starttime, self.simtime[-1]])
        else:
            err = 'evaltime must be a number, a 1D numpy array with two values or None.\n \
                Please provide a valid evaltime.\n'
            raise ValueError(err)

        self.eval_idx = np.array(
            [np.where(self.simtime <= self.evaltime[0])[0][-1], np.where(self.simtime <= self.evaltime[1])[0][-1]]
        )

        self.stabilized = False
        self.evaluator = Evaluation(data_out)

    def __repr__(self):
        return f'BSMBase(data_in={self.data_in}, timesteps={len(self.timesteps)}, \
        endtime={self.endtime}, evaltime={self.evaltime})'

    def step(self, *args, **kwargs):
        """Abstract method to perform a simulation step.

        This method must be implemented by all child classes.
        It defines how the model advances by one timestep.

        Raises
        ------
        NotImplementedError
            If the child class does not implement this method.
        """
        raise NotImplementedError('Child classes must implement the step() method.')

    def simulate(self, *args, **kwargs):
        """Abstract method to perform a simulation.

        This method must be implemented by all child classes.
        It offers a convenient way to run the simulation for the entire time period.
        It should call the step() method for each timestep.

        Raises
        ------
        NotImplementedError
            If the child class does not implement this method.
        """
        raise NotImplementedError('Child classes must implement the simulate() method.')

    def _stabilize(self, check_vars: list[str], atol: float = 1e-3):
        """Stabilizes the plant.

        Parameters
        ----------
        check_vars : list[str]
            List of attribute names (as strings) to check for stabilization. <br>
            All attributes must be of the same type and have the same shape.
        atol : float (optional)
            Absolute tolerance for the stabilization. <br>
            Default is 1e-3.

        Returns
        -------
        stable : bool
            Returns `True` if plant is stabilized after iterations.
        """
        # Get initial values of the attributes to check
        old_check_vars = np.array([getattr(self, var) for var in check_vars], dtype=float)
        stable = False
        i = 0
        s = 0  # index of the timestep to call repeatedly until stabilization
        while not stable:
            i += 1
            logger.debug('Stabilizing iteration %s', i)
            self.step(s)
            new_check_vars = np.array([getattr(self, var) for var in check_vars], dtype=float)
            # Check if the absolute difference is within the tolerance
            if np.isclose(new_check_vars, old_check_vars, atol=atol).all():
                stable = True
            old_check_vars = new_check_vars
        logger.info('Stabilized after %s iterations\n', i)
        self.stabilized = True
        return stable

    @staticmethod
    def _create_copies(in_arr: np.ndarray | list[np.ndarray], n_copies: int = 1) -> list[np.ndarray]:
        """Creates copies of the input arrays.
        Parameters
        ----------
        in_arr : np.ndarray(21) | list[np.ndarray(21)]
            ASM1 array or list of ASM1 arrays to be copied. \n
            [SI, SS, XI, XS, XBH, XBA, XP, SO, SNO, SNH, SND, XND, SALK, TSS, Q, TEMP,
            SD1, SD2, SD3, XD4, XD5]
        n_copies : int (optional)
            Number of copies to create. Default is 1.

        Returns
        -------
        out : list[np.ndarray(21)]
            List of copied ASM1 arrays.
        """
        if isinstance(in_arr, np.ndarray):
            in_arr = [in_arr] * n_copies
        elif isinstance(in_arr, list):
            in_arr = [np.array(arr) for arr in in_arr]
        else:
            raise ValueError('Input must be a numpy array or a list of numpy arrays.')

        out = [np.copy(arr) for arr in in_arr]
        return out
