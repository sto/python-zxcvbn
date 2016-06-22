
import math
import re

import zxcvbn.adjacency


def calc_average_degree(graph):
    average = 0.0
    for neighbors in graph.values():
        average += len([n for n in neighbors if n])
    average /= len(graph)
    return average


BRUTEFORCE_CARDINALITY = 10
MIN_GUESSES_BEFORE_GROWING_SEQUENCE = 10000
MIN_SUBMATCH_GUESSES_SINGLE_CHAR = 10
MIN_SUBMATCH_GUESSES_MULTI_CHAR = 50
MIN_SUBMATCH_GUESSES_MULTI_CHAR = 50


def nCk(n, k):
    # http://blog.plover.com/math/choose.html
    if k > n:
        return 0
    if k == 0:
        return 1
    r = 1
    for d in range(1, k):
      r *= n
      r /= d
      n -= 1
    return r


  # ------------------------------------------------------------------------------
  # search --- most guessable match sequence -------------------------------------
  # ------------------------------------------------------------------------------
  #

  # ------------------------------------------------------------------------------

def most_guessable_match_sequence(password, matches, _exclude_additive=False):
    """
      Takes a sequence of overlapping matches, returns the non-overlapping sequence with
      minimum guesses. the following is a O(l_max * (n + m)) dynamic programming algorithm
      for a length-n password with m candidate matches. l_max is the maximum optimal
      sequence length spanning each prefix of the password. In practice it rarely exceeds 5 and the
      search terminates rapidly.
     
      the optimal "minimum guesses" sequence is here defined to be the sequence that
      minimizes the following function:
     
         l! * Product(m.guesses for m in sequence) + D^(l - 1)
     
      where l is the length of the sequence.
     
      the factorial term is the number of ways to order l patterns.
     
      the D^(l-1) term is another length penalty, roughly capturing the idea that an
      attacker will try lower-length sequences first before trying length-l sequences.
     
      for example, consider a sequence that is date-repeat-dictionary.
       - an attacker would need to try other date-repeat-dictionary combinations,
         hence the product term.
       - an attacker would need to try repeat-date-dictionary, dictionary-repeat-date,
         ..., hence the factorial term.
       - an attacker would also likely try length-1 (dictionary) and length-2 (dictionary-date)
         sequences before length-3. assuming at minimum D guesses per pattern type,
         D^(l-1) approximates Sum(D^i for i in [1..l-1]
    """
    n = len(password)

    # partition matches into sublists according to ending index j
    matches_by_j = [[] for _ in range(0,n)]
    for m in matches:
        matches_by_j[m['j']].append(m)

    optimal = {
        # optimal['m'][k][l] holds final match in the best length-l match sequence covering the
        # password prefix up to k, inclusive.
        # if there is no length-l sequence that scores better (fewer guesses) than
        # a shorter match sequence spanning the same prefix, optimal.m[k][l] is undefined.
        'm':  [{} for _ in range(0, n)],

        # same structure as optimal['m'], except holds the product term Prod(m.guesses for m in sequence).
        # optimal['pi'] allows for fast (non-looping) updates to the minimization function.
        'pi':  [{} for _ in range(0, n)],

        # optimal['g'][k] holds the lowest guesses up to k according to the minimization function.
        'g':  [float('inf') for _ in range(0, n)],

        # optimal.['l'][k] holds the length, l, of the optimal sequence covering up to k.
        # (this is also the largest key in optimal.['m'][k] and optimal['pi'][k] objects)
        'l':  [0 for _ in range(0, n)]
    }
   
    def update(m, l):
        """ helper: considers whether a length-l sequence ending at match m is better (fewer guesses)
            than previously encountered sequences, updating state if so.
        """
        k = m['j']
        pi = estimate_guesses(m, password)
        if l > 1:
            # we're considering a length-l sequence ending with match m:
            # obtain the product term in the minimization function by multiplying m's guesses
            # by the product of the length-(l-1) sequence ending just before m, at m.i - 1.
            pi *= optimal['pi'][m['i'] - 1][l - 1]
        # calculate the minimization func
        g = math.factorial(l) * pi
        if not _exclude_additive:
            g += MIN_GUESSES_BEFORE_GROWING_SEQUENCE ** (l - 1)
        # update state if new best
        if g < optimal['g'][k]:
            optimal['g'][k] = g
            optimal['l'][k] = l
            optimal['m'][k][l] = m
            optimal['pi'][k][l] = pi

    def bruteforce_update(k):
        """ helper: considers whether bruteforce matches ending at position k are optimal.
        """
        # three cases to consider...
        # case 1: a bruteforce match spanning the full prefix.
        m = make_bruteforce_match(0, k)
        update(m, 1)
        if k == 0:
            return 
        for l, last_m in optimal['m'][k - 1].items():
            #l = int(l)
            if last_m['pattern'] == 'bruteforce':
                # case 2: if the optimal length-l sequence up to k - 1 ended in a bruteforce match,
                # consider whether extending it by one character is optimal up to k.
                # this preserves the sequence length l.
                m = make_bruteforce_match(last_m['i'], k)
                update(m, l)
            else:
                # case 3: if the optimal length-l sequence up to k - 1 ends in a non-bruteforce match,
                # consider whether starting a new single-character bruteforce match is optimal.
                # this adds a new match, adding 1 to the prior sequence length l.
                m = make_bruteforce_match(k, k)
                update(m, l + 1)

    def make_bruteforce_match(i, j):
        """ helper: make bruteforce match objects spanning i to j, inclusive.
        """
        return dict(pattern='bruteforce', token=password[i:j+1], i=i, j=j)

    def unwind(n):
        """ helper: step backwards through optimal['m'] starting at the end,
            constructing the final optimal match sequence.
        """
        optimal_match_sequence = []
        k = n - 1
        l = optimal['l'][k]
        while k >= 0:
            m = optimal['m'][k][l]
            optimal_match_sequence.insert(0, m)
            k = m['i'] - 1
            l -= 1
        return optimal_match_sequence

    for k in range(0, n):
        for m in matches_by_j[k]:
            if m['i'] > 0:
                for l in optimal['m'][m['i'] - 1].keys():
                    #l = parseInt(l)
                    update(m, l + 1)
            else:
                update(m, 1)
        bruteforce_update(k)
    import json
    optimal_match_sequence = unwind(n)

    # corner: empty password
    if len(password) == 0:
        guesses = 1
    else:
        guesses = optimal['g'][n - 1]

    # final result object
    return dict(password=password, guesses=guesses,
                guesses_log10=math.log(guesses, 10),
                sequence=optimal_match_sequence)

# ------------------------------------------------------------------------------
# guess estimation -- one function per match pattern ---------------------------
# ------------------------------------------------------------------------------

def bruteforce_guesses(match):
    guesses = BRUTEFORCE_CARDINALITY ** len(match['token'])
    # small detail: make bruteforce matches at minimum one guess bigger than smallest allowed
    # submatch guesses, such that non-bruteforce submatches over the same [i..j] take precidence.
    min_guesses = MIN_SUBMATCH_GUESSES_SINGLE_CHAR + 1 if len(match['token']) == 1 \
            else MIN_SUBMATCH_GUESSES_MULTI_CHAR + 1
    return max(guesses, min_guesses) 

def repeat_guesses(match):
    return match['base_guesses'] * match['repeat_count']

def sequence_guesses(match):
    first_chr = match['token'][0]
    # lower guesses for obvious starting points
    if first_chr in ['a', 'A', 'z', 'Z', '0', '1', '9']:
        base_guesses = 4
    else:
        if first_chr.isdigit():
            base_guesses = 10 # digits
        else:
            # could give a higher base for uppercase,
            # assigning 26 to both upper and lower sequences is more conservative.
            base_guesses = 26
    if not match['ascending']:
        # need to try a descending sequence in addition to every ascending sequence ->
        # 2x guesses
        base_guesses *= 2
    return base_guesses * len(match['token'])

MIN_YEAR_SPACE = 20
REFERENCE_YEAR = 2016

def regex_guesses(match):
    char_class_bases = dict(alpha_lower=26, alpha_upper=26,
                            alpha=52, alphanumeric=62,
                            digits=10, symbols=33)
    if match['regex_name'] in char_class_bases:
        return char_class_bases[match['regex_name']] ** len(match['token'])
    elif match['regex_name'] == 'recent_year':
        # conservative estimate of year space: num years from REFERENCE_YEAR.
        # if year is close to REFERENCE_YEAR, estimate a year space of MIN_YEAR_SPACE.
        year_space = abs(int(match['regex_match'][0]) - REFERENCE_YEAR)
        return max(year_space, MIN_YEAR_SPACE)

def date_guesses(match):
    # base guesses: (year distance from REFERENCE_YEAR) * num_days * num_years
    year_space = max(abs(match['year'] - REFERENCE_YEAR), MIN_YEAR_SPACE)
    guesses = year_space * 365
    # double for four-digit years
    if 'has_full_year' in match and match['has_full_year']:
        guesses *= 2 
    # add factor of 4 for separator selection (one of ~4 choices)
    if match['separator']:
        guesses *= 4 
    return guesses

KEYBOARD_AVERAGE_DEGREE = calc_average_degree(zxcvbn.adjacency.graphs['qwerty'])
# slightly different for keypad/mac keypad, but close enough
KEYPAD_AVERAGE_DEGREE = calc_average_degree(zxcvbn.adjacency.graphs['keypad'])

KEYBOARD_STARTING_POSITIONS =len(zxcvbn.adjacency.graphs['qwerty'])
KEYPAD_STARTING_POSITIONS = len(zxcvbn.adjacency.graphs['keypad'])

def spatial_guesses(match):
    if match['graph'] in ['qwerty', 'dvorak']:
        s = KEYBOARD_STARTING_POSITIONS
        d = KEYBOARD_AVERAGE_DEGREE
    else:
        s = KEYPAD_STARTING_POSITIONS
        d = KEYPAD_AVERAGE_DEGREE
    guesses = 0
    L = len(match['token'])
    t = match['turns']
    # estimate the number of possible patterns w/ length L or less with t turns or less.
    for i in range(2, L):
        possible_turns = min(t, i - 1)
        for j in range(1, possible_turns):
            guesses += nCk(i - 1, j - 1) * s * (d ** j)
    # add extra guesses for shifted keys. (% instead of 5, A instead of a.)
    # math is similar to extra guesses of l33t substitutions in dictionary matches.
    if match['shifted_count']:
        S = match['shifted_count']
        U = len(match['token']) - S  # unshifted count
        if S == 0 or U == 0:
            guesses *= 2
        else:
            shifted_variations = 0
            for i in range(1,min(S, U)):
                shifted_variations += nCk(S + U, i) 
            guesses *= shifted_variations
    return guesses

def dictionary_guesses(match):
    match['base_guesses'] = match['rank']   # keep these as properties for display purposes
    match['uppercase_variations'] = uppercase_variations(match)
    match['l33t_variations'] = l33t_variations(match)
    reversed_variations = 2 if match['reversed'] else 1
    # ensure user_inputs matches take precedence
    match['bonus'] = 0 if match['dictionary_name'] == 'user_inputs' else 1
    return match['base_guesses'] * match['uppercase_variations'] * match['l33t_variations'] * reversed_variations

START_UPPER = re.compile(r'^[A-Z][^A-Z]+$')
END_UPPER = re.compile(r'^[^A-Z]+[A-Z]$')
ALL_UPPER = re.compile(r'^[^a-z]+$')
ALL_LOWER = re.compile(r'^[^A-Z]+$')

def uppercase_variations(match):
    word = match['token']
    if ALL_LOWER.match(word) or word.lower() == word:
        return 1 
    # a capitalized word is the most common capitalization scheme,
    # so it only doubles the search space (uncapitalized + capitalized).
    # allcaps and end-capitalized are common enough too, underestimate as 2x factor to be safe.
    for regex in [START_UPPER, END_UPPER, ALL_UPPER]:
        if regex.match(word):
            return 2
    # otherwise calculate the number of ways to capitalize U+L uppercase+lowercase letters
    # with U uppercase letters or less. or, if there's more uppercase than lower (for eg. PASSwORD),
    # the number of ways to lowercase U+L letters with L lowercase letters or less.
    U = len([chr for chr in word if chr.isupper()])
    L = len([chr for chr in word if chr.islower()])
    variations = 0
    for i in range(1, min(U, L)):
        variations += nCk(U + L, i) 
    return variations

def l33t_variations(match):
    if not match['l33t']:
        return 1 
    variations = 1
    for subbed, unsubbed in match['sub'].items():
        # lower-case match.token before calculating: capitalization shouldn't affect l33t calc.
        chrs = match['token'].lower()
        S = len([chr for chr in chrs if chr == subbed])   # num of subbed chars
        U = len([chr for chr in chrs if chr == unsubbed]) # num of unsubbed chars
        if S == 0 or U == 0:
            # for this sub, password is either fully subbed (444) or fully unsubbed (aaa)
            # treat that as doubling the space (attacker needs to try fully subbed chars in addition to
            # unsubbed.)
            variations *= 2
        else:
            # this case is similar to capitalization:
            # with aa44a, U = 3, S = 2, attacker needs to try unsubbed + one sub + two subs
            p = min(U, S)
            possibilities = 0
            for i in range(1, p):
                possibilities += nCk(U + S, i) 
            variations *= possibilities
    return variations

def estimate_guesses(match, password):
    if 'guesses' in match:
        return match['guesses']  # a match's guess estimate doesn't change. cache it.
    min_guesses = 1
    if len(match['token']) < len(password):
        min_guesses = MIN_SUBMATCH_GUESSES_SINGLE_CHAR if len(match['token']) == 1 \
                else MIN_SUBMATCH_GUESSES_MULTI_CHAR
    
    estimation_functions = dict(
      bruteforce=bruteforce_guesses,
      dictionary=dictionary_guesses,
      spatial=spatial_guesses,
      repeat=repeat_guesses,
      sequence=sequence_guesses,
      regex=regex_guesses,
      date=date_guesses)

    guesses = estimation_functions[match['pattern']](match)
    match['guesses'] = max(guesses, min_guesses)
    if 'bonus' in match:
        match['guesses'] += match['bonus']
    match['guesses_log10'] = math.log(match['guesses'], 10)
    return match['guesses']



