# lib/strategies/precio.py
from __future__ import annotations
from abc import ABC, abstractmethod

class PrecioStrategy(ABC):
    @abstractmethod
    def utilidad(self, qty: float, unit_price: float, unit_cost: float) -> float:
        ...

class MargenDirecto(PrecioStrategy):
    def utilidad(self, qty: float, unit_price: float, unit_cost: float) -> float:
        # Utilidad = (precio - costo) * cantidad
        return qty * (unit_price - unit_cost)

class PrecioFactory:
    @classmethod
    def get(cls, **_kwargs) -> PrecioStrategy:
        return MargenDirecto()
