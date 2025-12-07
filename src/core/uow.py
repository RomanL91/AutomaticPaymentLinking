from abc import ABC, abstractmethod


class IUnitOfWork(ABC):
    """Интерфейс Unit of Work."""
    
    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def __aenter__(self):
        raise NotImplementedError
    
    @abstractmethod
    async def __aexit__(self, *args):
        raise NotImplementedError
    
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError