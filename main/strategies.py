from abc import ABC, abstractmethod
from django.db import transaction
from typing import Tuple, Optional
from main.repositories import PurchaseRepository, UserRepository


class PurchaseStrategy(ABC):
    @abstractmethod
    def can_purchase(self, user, course) -> Tuple[bool, Optional[str]]:
        pass

    @abstractmethod
    def execute(self, user, course):
        pass


class BalancePurchaseStrategy(PurchaseStrategy):
    def can_purchase(self, user, course):
        if PurchaseRepository.exists(user, course):
            return False, "Course already purchased"
        
        if int(user.balance or 0) < int(getattr(course, 'price', 0) or 0):
            return False, "Balance not enough"
        return True, None

    def execute(self, user, course):
        with transaction.atomic():
            UserRepository.change_balance(user, -int(getattr(course, 'price', 0) or 0))
            purchase = PurchaseRepository.create(user, course)
            return purchase


class FreePurchaseStrategy(PurchaseStrategy):
    def can_purchase(self, user, course):
        if PurchaseRepository.exists(user, course):
            return False, "Course already purchased"
        return True, None

    def execute(self, user, course):
        return PurchaseRepository.create(user, course)


def get_purchase_strategy(course) -> PurchaseStrategy:
    if getattr(course, 'price', 0) == 0:
        return FreePurchaseStrategy()
    
    return BalancePurchaseStrategy()