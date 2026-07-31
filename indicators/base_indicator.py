from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):

    @abstractmethod
    def calculate(self, data: pd.DataFrame):
        pass