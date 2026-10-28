from abc import ABC, abstractmethod

class AbstractVNA(ABC):
    """
    The Hardware Abstraction Layer parent class. 
    Defines the contract for what ANY VNA must be able to do in our factory.
    """
    def __init__(self, resource_address: str):
        self.resource_address = resource_address
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """Establishes physical or virtual connection via PyVISA."""
        pass

    @abstractmethod
    def set_if_bandwidth(self, bandwidth_hz: int) -> None:
        """Sets internal digital filtering window size."""
        pass

    @abstractmethod
    def capture_s21_trace(self) -> list:
        """Executes a high-frequency forward transmission sweep."""
        pass
