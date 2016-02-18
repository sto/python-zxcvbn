import time

from zxcvbn.matching import omnimatch
from zxcvbn.scoring import minimum_entropy_match_sequence
from zxcvbn.feedback import get_feedback

def password_strength(password, user_inputs=[]):
    start = time.time()
    matches = omnimatch(password, user_inputs)
    result = minimum_entropy_match_sequence(password, matches)
    result.feedback = get_feedback(result.score, result.feedback)
    result['calc_time'] = time.time() - start
    return result
