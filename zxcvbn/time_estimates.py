

def estimate_attack_times(guesses):
    crack_times_seconds = dict(online_throttling_100_per_hour=guesses / (100.0 / 3600),
                               online_no_throttling_10_per_second=guesses / 10.0,
                               offline_slow_hashing_1e4_per_second=guesses / 1.0e4,
                               offline_fast_hashing_1e10_per_second=guesses / 1.0e10)

    crack_times_display = {scenario: display_time(seconds)
                           for scenario, seconds in crack_times_seconds.items()}

    return dict(crack_times_seconds=crack_times_seconds,
                crack_times_display=crack_times_display,
                score=guesses_to_score(guesses))


def guesses_to_score(guesses):
    delta = 5
    if guesses < 1e3 + delta:
      # risky password: "too guessable"
      return 0
    elif guesses < 1e6 + delta:
      # modest protection from throttled online attacks: "very guessable"
      return 1
    elif guesses < 1e8 + delta:
      # modest protection from unthrottled online attacks: "somewhat guessable"
      return 2
    elif guesses < 1e10 + delta:
      # modest protection from offline attacks: "safely unguessable"
      # assuming a salted, slow hash function like bcrypt, scrypt, PBKDF2, argon, etc
      return 3
    else:
      # strong protection from offline attacks under same scenario: "very unguessable"
      return 4

def display_time(seconds):
    minute = 60
    hour = minute * 60
    day = hour * 24
    month = day * 31
    year = month * 12
    century = year * 100
    if seconds < 1:
      return None, 'less than a second'
    elif seconds < minute:
      base = round(seconds)
      return "{} second{}".format(base, 's' if base != 1 else '')
    elif seconds < hour:
      base = round(seconds / minute)
      return "{} minute{}".format(base, 's' if base != 1 else '')
    elif seconds < day:
      base = round(seconds / hour)
      return "{} hour{}".format(base, 's' if base != 1 else '')
    elif seconds < month:
      base = round(seconds / day)
      return "{} day{}".format(base, 's' if base != 1 else '')
    elif seconds < year:
      base = round(seconds / month)
      return "{} month{}".format(base, 's' if base != 1 else '')
    elif seconds < century:
      base = round(seconds / year)
      return "{} year{}".format(base, 's' if base != 1 else '')
    else:
      return 'centuries'
