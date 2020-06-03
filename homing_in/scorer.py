import logging

logger = logging.getLogger(__name__)


class Scorer:
    @classmethod
    def value_map(cls, key_val: int, mapping: dict):
        assert 'other' in mapping, 'mapping must contain "other" key'
        try:
            score = mapping[key_val]
        except KeyError:
            score = mapping['other']
            logger.debug(f'score, mapping: {key_val} to "other"')
        return score

    @classmethod
    def price(cls, price: int, max_desired: int, score_per_under: int, score_per_over: int,
              units: int):
        diff_to_desired = (max_desired - price) / units
        if diff_to_desired == 0:
            score = 0
        elif diff_to_desired > 0:
            score = diff_to_desired * score_per_under
        else:  # diff_to_desired < 0
            score = abs(diff_to_desired) * score_per_over
        return score

    @classmethod
    def travel_time(cls, minutes: float, ideal_minutes: int, bad_minutes: int, ideal_score,
                    over_ideal_cost: float, over_bad_cost: float) -> float:
        """

        :param minutes: estimated travel time
        :param ideal_minutes: any time below this get a score of ideal_score
        :param bad_minutes: any time above this gets an increased rate of negative score
        :param ideal_score: maximum score
        :param over_ideal_cost: for every minute over ideal_minutes, penalise score by this amount
        :param over_bad_cost: for every minute over bad_minutes, penalise score by this amount
        :return:
        """
        assert over_ideal_cost < 0 and over_bad_cost <0, 'costs should both be negative'
        score = ideal_score
        if minutes > ideal_minutes:
            score += (min([minutes, bad_minutes]) - ideal_minutes) * over_ideal_cost
            if minutes > bad_minutes:
                score += (minutes - bad_minutes) * over_bad_cost
        return score


if __name__ == '__main__':
    a = Scorer.travel_time(50, 30, 50, 10, -0.5, -3)
