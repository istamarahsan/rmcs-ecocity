from dataclasses import dataclass
import random
from typing import Tuple, List, Dict, Union

@dataclass
class Policy:
    title: str
    description: str
    cashCost: int
    popularity: int
    
    cash_on_accept: int
    food_on_accept: int
    power_on_accept: int
    pollution_on_accept: int
    industry_on_accept: int
    reputation_on_accept: int

    cash_on_reject: int
    food_on_reject: int
    power_on_reject: int
    pollution_on_reject: int
    industry_on_reject: int
    reputation_on_reject: int

@dataclass
class EcoCityPlayerStats:
    money: int
    food: int
    reputation: int
    pollution: int
    oil_power_amount: int
    tidal_power_amount: int

    def to_tuple(self) -> Tuple[int, int, int, int, int, int]:
        return (self.money, self.food, self.reputation, self.pollution, self.oil_power_amount, self.tidal_power_amount)

@dataclass
class Power:
    name: str
    power_cost: int
    pollution: int

class EcoCity:
    # util
    rand: random.Random

    # state
    money: int
    food: int
    reputation: int
    pollution: int
    turn_number: int
    active_policy_options: List[int]
    policy_cooldowns: Dict[int, int]
    powerAmounts: Dict[str, int]

    # policy content
    powers: Dict[str, Power] = {
        "Oil": Power(
            "Oil",
            250,
            2
        ),
        "Tidal": Power(
            "Tidal",
            500,
            1
        )
    }
    policies: Dict[int, Policy] = {
        0: Policy(
            "RobbinFood",
            "",
            500,60,-1000,0,0,0,0,5,0,-3,0,0,0,-5
        ),
        1: Policy(
            "PetroBigBro",
            "",
            2000,50,5000,0,0,-3,0,8,0,0,0,0,-3,5
        ),
        2: Policy(
            "RedGreenBurn","",
            2000,60,-5000,0,0,10,0,5,0,0,0,30,0,-10
        ),
        3: Policy(
            "PlantGrant", "",
            2000,50,-2000,0,0,-8,0,3,0,0,0,-5,3,8
        ),
        4: Policy(
            "TreeToFood", "",
            500,30,5000,0,0,8,10,-10,-2000,-5,0,0,-10,10
        ),
        5: Policy(
            "NoWayHome", "",
            500,50,-1000,0,0,3,0,5,0,0,0,0,-3,3
        )
    }
    max_power_amount: int = 15
    minimum_money_gain_after_producing_food: int = 500
    maximum_money_gain_after_producing_food: int = 1000
    food_production_power_cost: int = 2
    food_production_money_cost: int = 600
    food_production_rate: int = 3
    minimum_popularity_impact: int = 5
    maximum_popularity_impact: int = 15

    def __init__(self) -> None:
        pass

    def reset(self, seed: int) -> Tuple[Tuple[int, int, int, EcoCityPlayerStats], Dict[str, any]]: 
        self.rand = random.Random(seed)
        self.money = 5000
        self.food = 10
        self.reputation = 100
        self.pollution = 0
        self.turn_number = 0
        self.policy_cooldowns = { i:0 for i in self.policies.keys() }
        self.active_policy_options = self._draw_policies()
        self.powerAmounts = { "Oil": 10, "Tidal":3 }
        stats = self._get_stats()
        return ((*self.active_policy_options, stats), {})


    def step(self, action: Tuple[int, bool]) -> Tuple[Tuple[int, int, int, EcoCityPlayerStats], float, bool, bool, Dict[str, any]]:
        # process power generation
        total_power = sum(self.powerAmounts.values())
        while (total_power < self.max_power_amount):
            try_select_random_power = self.rand.randint(0, 1) == 1
            chosen_power_id: Union[str, None] = None
            if try_select_random_power:
                chosen_power_id = self.rand.choice(list(self.powers.keys()))
                if (self.powers[chosen_power_id].power_cost > self.money):
                    chosen_power_id = self._get_affordable_power_with_lowest_pollution()
            else:
                chosen_power_id = self._get_affordable_power_with_lowest_pollution()
            if not chosen_power_id:
                break
            chosen_power = self.powers[chosen_power_id]
            self.powerAmounts[chosen_power_id] += 1
            self.money -= chosen_power.power_cost
            self.pollution += chosen_power.pollution
            total_power = sum(self.powerAmounts.values())
        
        # process food production
        if (sum(self.powerAmounts.values()) >= self.food_production_power_cost 
            and self.money >= self.food_production_money_cost):
            self.food += self.food_production_rate
            self.money -= self.food_production_money_cost
            for _ in range(self.food_production_power_cost):
                options = [power for power in self.powers.keys() if self.powerAmounts[power] > 0]
                chosen_option = self.rand.choice(options)
                self.powerAmounts[chosen_option] -= 1
            self.money += self.rand.randrange(self.minimum_money_gain_after_producing_food, self.maximum_money_gain_after_producing_food)

        # process cooldowns
        self.policy_cooldowns = { k: max(0, v-1) for k, v in self.policy_cooldowns.items() }
        
        # parse the action 
        chosen_index, policy_was_accepted = action
        chosen_policy_id = self.active_policy_options[chosen_index]
        chosen_policy = self.policies[chosen_policy_id]

        # chosen policy cooldown is 3. other options are 1.
        for policy_option in self.active_policy_options:
            self.policy_cooldowns[policy_option] = 3 if policy_option == chosen_policy_id else 1

        # apply effects
        if policy_was_accepted:
            self.money += chosen_policy.cash_on_accept
            self.food += chosen_policy.food_on_accept
            self.pollution += chosen_policy.pollution_on_accept
            self.reputation += chosen_policy.reputation_on_accept
        else:
            self.money += chosen_policy.cash_on_reject
            self.food += chosen_policy.food_on_reject
            self.pollution += chosen_policy.pollution_on_reject
            self.reputation += chosen_policy.reputation_on_reject

        # apply popularity effects on reputation
        popularity_impact = self.rand.randrange(self.minimum_popularity_impact, self.maximum_popularity_impact)
        self.reputation += popularity_impact * (
            1 if 
                (chosen_policy.popularity >= 50 and policy_was_accepted) 
                or (chosen_policy.popularity < 50 and not policy_was_accepted)
            else -1
        )

        self.money -= chosen_policy.cashCost

        # clamp values
        self.money = max(0, self.money)
        self.pollution = max(0, self.pollution)

        is_game_over = self._is_game_over()

        if not is_game_over:
            # next policies
            self.active_policy_options = self._draw_policies()
            self.turn_number += 1
        
        return (
            (*self.active_policy_options,
             self._get_stats()),
            -10 if is_game_over else 10,
            is_game_over,
            is_game_over,
            {}
        )

    def _is_game_over(self) -> bool:
        return self.money <= 0 or self.food <= 0 or self.reputation <= 0 or self.pollution >= 100

    def _draw_policies(self) -> List[int]:
        possible_policy_ids = [id for id, cooldown in self.policy_cooldowns.items() if cooldown == 0]
        draw = self.rand.sample(possible_policy_ids, 3) if len(possible_policy_ids) > 3 else [
            *possible_policy_ids, 
            *self.rand.sample([id for id in self.policies.keys() if id not in possible_policy_ids]
                              , 3-len(possible_policy_ids))
        ]
        return draw
    
    def _get_stats(self) -> EcoCityPlayerStats:
        return EcoCityPlayerStats(
            money=self.money,
            food=self.food,
            reputation=self.reputation,
            pollution=self.pollution,
            oil_power_amount=self.powerAmounts["Oil"],
            tidal_power_amount=self.powerAmounts["Tidal"]
        )
    
    def _get_affordable_power_with_lowest_pollution(self) -> Union[str, None]:
        options = list(self.powers.values()).copy()
        options.sort(key=lambda p: p.pollution)
        for option in options:
            if option.power_cost <= self.money:
                return option.name
        return None