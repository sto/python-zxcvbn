import time

import zxcvbn.matching
import zxcvbn.scoring
import zxcvbn.feedback
import zxcvbn.time_estimates

def password_strength(password, user_inputs=[]):
    start = time.time()
    matches = zxcvbn.matching.omnimatch(password, user_inputs)
    if matches:
        result = zxcvbn.scoring.most_guessable_match_sequence(password, matches)
        result['calc_time'] = time.time() - start

        attack_times = zxcvbn.time_estimates.estimate_attack_times(result['guesses'])
        result.update(attack_times)

        result['feedback'] = zxcvbn.feedback.get_all_feedback(result['score'], result['sequence'])

    else:
         result = {}
         result['feedback'] = zxcvbn.feedback.get_all_feedback(0, [])        
    return result

