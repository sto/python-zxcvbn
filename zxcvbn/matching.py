from itertools import groupby
import pkg_resources
import re

try:
    import simplejson as json
    json # silences pyflakes :<
except ImportError:
    import json


import zxcvbn.adjacency
import zxcvbn.scoring 


RANKED_DICTIONARIES = {}


def translate(string, chr_map):
    out = ''
    for char in string:
        out += chr_map[char] if char in chr_map else char
    return out




#-------------------------------------------------------------------------------
# dictionary match (common passwords, english, last names, etc) ----------------
#-------------------------------------------------------------------------------

def dictionary_match(password, _ranked_dictionaries=RANKED_DICTIONARIES):
    matches = []
    length = len(password)

    pw_lower = password.lower()

    for dict_name, ranked_dict in _ranked_dictionaries.items():
        for i in range(0, length):
            for j in range(i, length):
                word = pw_lower[i:j+1]
                if word in ranked_dict:
                    rank = ranked_dict[word]
                    matches.append(dict(pattern='dictionary',
                                        i=i, j=j,
                                        token=password[i:j+1],
                                        matched_word=word,
                                        rank=rank,
                                        l33t=False,
                                        reversed=False,
                                        dictionary_name=dict_name))
    return matches


# def _build_dict_matcher(dict_name, ranked_dict):
#     def func(password):
#         # Regular dictionary matches
#         matches = dictionary_match(password, ranked_dict)
#         for match in matches:
#             match['dictionary_name'] = dict_name
#         return matches
#     return func


def reversed_dictionary_match(password, _ranked_dictionaries=RANKED_DICTIONARIES):
    matches = dictionary_match(password[::-1])
    for match in matches:
        match['token'] = match['token'][::-1]  # reverse token back
        match['reversed'] = True
        # map coordinates back to original string
        match['i'], match['j'] = len(password) - 1 - match['j'], len(password) - 1 - match['i']
    return matches


def _build_ranked_dict(unranked_list):
    result = {}
    i = 1
    for word in unranked_list:
        result[word.lower()] = i
        i += 1
    return result


def _set_user_input_dictionary(ordered_list):
    """ Sets the user inputs dictionary """
    RANKED_DICTIONARIES['user_inputs'] = _build_ranked_dict(ordered_list)


def _load_frequency_lists():
    data = pkg_resources.resource_string(__name__, 'generated/frequency_lists.json')
    dicts = json.loads(data.decode())
    for name, wordlist in dicts.items():
        RANKED_DICTIONARIES[name] = _build_ranked_dict(wordlist)





_load_frequency_lists()

#-------------------------------------------------------------------------------
# dictionary match with common l33t substitutions ------------------------------
#-------------------------------------------------------------------------------

L33T_TABLE = {
  'a': ['4', '@'],
  'b': ['8'],
  'c': ['(', '{', '[', '<'],
  'e': ['3'],
  'g': ['6', '9'],
  'i': ['1', '!', '|'],
  'l': ['1', '|', '7'],
  'o': ['0'],
  's': ['$', '5'],
  't': ['+', '7'],
  'x': ['%'],
  'z': ['2'],
}

# makes a pruned copy of L33T_TABLE that only includes password's possible substitutions
def relevant_l33t_subtable(password):
    password_chars = set(password)

    filtered = {}
    for letter, subs in L33T_TABLE.items():
        relevent_subs = [sub for sub in subs if sub in password_chars]
        if len(relevent_subs) > 0:
            filtered[letter] = relevent_subs
    return filtered

# returns the list of possible 1337 replacement dictionaries for a given password

def enumerate_l33t_subs(table):
    subs = [[]]

    def dedup(subs):
        deduped = []
        members = set()
        for sub in subs:
            key = str(sorted(sub))
            if key not in members:
                deduped.append(sub)
        return deduped

    keys = list(table.keys())
    while len(keys) > 0:
        first_key = keys[0]
        rest_keys = keys[1:]
        next_subs = []
        for l33t_chr in table[first_key]:
            for sub in subs:
                dup_l33t_index = -1
                for i in range(0, len(sub)):
                    if sub[i][0] == l33t_chr:
                        dup_l33t_index = i
                        break
                if dup_l33t_index == -1:
                    sub_extension = list(sub)
                    sub_extension.append((l33t_chr, first_key))
                    next_subs.append(sub_extension)
                else:
                    sub_alternative = list(sub)
                    sub_alternative.pop(dup_l33t_index)
                    sub_alternative.append((l33t_chr, first_key))
                    next_subs.append(sub)
                    next_subs.append(sub_alternative)
        subs = dedup(next_subs)
        keys = rest_keys
    return map(dict, subs)


def l33t_match(password, _ranked_dictionaries=RANKED_DICTIONARIES):
    matches = []

    for sub in enumerate_l33t_subs(relevant_l33t_subtable(password)):
        if len(sub) == 0:
            break
        subbed_password = translate(password, sub)
        
        for match in dictionary_match(subbed_password):
            token = password[match['i']:match['j'] + 1]
            if token.lower() == match['matched_word']:
                continue  # only return the matches that contain an actual substitution
            match_sub = {}  # subset of mappings in sub that are in use for this match
            for subbed_chr, char in sub.items():
                if token.find(subbed_chr) != -1:
                    match_sub[subbed_chr] = char
            match['l33t'] = True
            match['token'] = token
            match['sub'] = match_sub
            match['sub_display'] = ', '.join([("%s -> %s" % (k, v)) for k, v in match_sub.items()])
            matches.append(match)
    # filter single-character l33t matches to reduce noise.
    # otherwise '1' matches 'i', '4' matches 'a', both very common English words
    # with low dictionary rank.
    return [match for match in matches if len(match['token']) > 1]

# ------------------------------------------------------------------------------
# spatial match (qwerty/dvorak/keypad) -----------------------------------------
# ------------------------------------------------------------------------------

def spatial_match(password):
    matches = []
    for graph_name, graph in zxcvbn.adjacency.graphs.items():
        matches.extend(spatial_match_helper(password, graph, graph_name))
    return matches


def spatial_match_helper(password, graph, graph_name):
    result = []
    i = 0
    while i < len(password) - 1:
        j = i + 1
        last_direction = None
        turns = 0
        shifted_count = 0
        while True:
            prev_char = password[j-1]
            found = False
            found_direction = -1
            cur_direction = -1
            adjacents = graph[prev_char] if prev_char in graph else []
            # consider growing pattern by one character if j hasn't gone over the edge.
            if j < len(password):
                cur_char = password[j]
                for adj in adjacents:
                    cur_direction += 1
                    if adj and adj.find(cur_char) != -1:
                        found = True
                        found_direction = cur_direction
                        if adj.find(cur_char) == 1:
                            # index 1 in the adjacency means the key is shifted, 0 means unshifted: A vs a, % vs 5, etc.
                            # for example, 'q' is adjacent to the entry '2@'. @ is shifted w/ index 1, 2 is unshifted.
                            shifted_count += 1
                        if last_direction != found_direction:
                            # adding a turn is correct even in the initial case when last_direction is null:
                            # every spatial pattern starts with a turn.
                            turns += 1
                            last_direction = found_direction
                        break
            # if the current pattern continued, extend j and try to grow again
            if found:
                j += 1
            # otherwise push the pattern discovered so far, if any...
            else:
                if j - i > 2: # don't consider length 1 or 2 chains.
                    result.append({
                        'pattern': 'spatial',
                        'i': i,
                        'j': j-1,
                        'token': password[i:j],
                        'graph': graph_name,
                        'turns': turns,
                        'shifted_count': shifted_count,
                    })
                # ...and then start a new search for the rest of the password.
                i = j
                break
    return result

#-------------------------------------------------------------------------------
# repeats (aaa, abcabcabc) and sequences (abcdef) ------------------------------
#-------------------------------------------------------------------------------


greedy = re.compile(r'(.+)\1+')
lazy = re.compile(r'(.+?)\1+')
lazy_anchored = re.compile(r'^(.+?)\1+$')

def repeat_match(password):
    matches = []
    last_index = 0

    while last_index < len(password):
        greedy_match = greedy.search(password[last_index:])
        lazy_match = lazy.search(password[last_index:])

        if not greedy_match:
            break

        if len(greedy_match.group(0)) > len(lazy_match.group(0)):
            # greedy beats lazy for 'aabaab'
            #   greedy: [aabaab, aab]
            #   lazy:   [aa,     a]
            match = greedy_match
            # greedy's repeated string might itself be repeated, eg.
            # aabaab in aabaabaabaab.
            # run an anchored lazy match on greedy's repeated string
            # to find the shortest repeated string
            #print(match.group(0))
            base_token = lazy_anchored.search(match.group(0)).group(1)

        else:
            # lazy beats greedy for 'aaaaa'
            #   greedy: [aaaa,  aa]
            #   lazy:   [aaaaa, a]
            match = lazy_match
            base_token = match.group(1)

        i, j = match.span(0)
        i += last_index
        j += last_index - 1
        
        # recursively match and score the base string
        base_analysis = zxcvbn.scoring.most_guessable_match_sequence(base_token, omnimatch(base_token))

        base_matches = base_analysis['sequence']
        base_guesses = base_analysis['guesses'] 
     
        matches.append(dict(pattern='repeat', i=i, j=j,
                            token=match.group(0), base_token=base_token,
                            base_guesses=base_guesses,
                            base_matches=base_matches,
                            repeat_count=len(match.group(0))/len(base_token)))

        last_index = j + 1

    return matches



MAX_DELTA = 5
def sequence_match(password):
    """ Identifies sequences by looking for repeated differences in unicode codepoint.
    this allows skipping, such as 9753, and also matches some extended unicode sequences
    such as Greek and Cyrillic alphabets.
    
    for example, consider the input 'abcdb975zy'
    
    password: a   b   c   d   b    9   7   5   z   y
    index:    0   1   2   3   4    5   6   7   8   9
    delta:      1   1   1  -2  -41  -2  -2  69   1
    
    expected result:
    [(i, j, delta), ...] = [(0, 3, 1), (5, 7, -2), (8, 9, 1)]
    """
    if len(password) == 1:
        return []

    result = []

    def update(i, j, delta):
        if j - i > 1 or abs(delta) == 1:
            if 0 < abs(delta) <= MAX_DELTA:
                token = password[i:j+1]
                if re.match(r'^[a-z]+$', token):
                    sequence_name = 'lower'
                    sequence_space = 26
                elif re.match(r'^[A-Z]+$', token):
                    sequence_name = 'upper'
                    sequence_space = 26
                elif re.match(r'^\d+$', token):
                    sequence_name = 'digits'
                    sequence_space = 10
                else:
                    # conservatively stick with roman alphabet size.
                    # (this could be improved)
                    sequence_name = 'unicode'
                    sequence_space = 26
          
                result.append(dict(pattern='sequence', i=i, j=j,
                                   token=password[i:j+1],
                                   sequence_name=sequence_name,
                                   sequence_space=sequence_space,
                                   ascending=delta > 0))

    i = 0
    last_delta = None

    for k in range(1, len(password)):
        delta = ord(password[k]) - ord(password[k - 1])
        if last_delta is None:
            last_delta = delta
        
        if delta == last_delta:
            continue
      
        j = k - 1
        update(i, j, last_delta)
        i = j
        last_delta = delta

    update(i, len(password) - 1, last_delta)
    return result


#-------------------------------------------------------------------------------
# regex matching ---------------------------------------------------------------
#-------------------------------------------------------------------------------

REGEXEN = dict(
    recent_year=re.compile(r'19\d\d|200\d|201\d'))

def regex_match(password, _regexen=REGEXEN):
    matches = []
    for name, regex in _regexen.items():
        for rx_match in regex.finditer(password):
            matches.append(dict(pattern='regex', token=rx_match.group(0),
                                i=rx_match.start(0), j=rx_match.end(0)-1,
                                regex_name=name, 
                                regex_match=[rx_match.group(0)] + list(rx_match.groups())))
    return matches

#-------------------------------------------------------------------------------
# date matching ----------------------------------------------------------------
#-------------------------------------------------------------------------------

DATE_MAX_YEAR = 2050
DATE_MIN_YEAR = 1000
DATE_SPLITS = {
  # for length-4 strings, eg 1191 or 9111, two ways to split:
  4: [(1, 2),  # 1 1 91 (2nd split starts at index 1, 3rd at index 2)
      (2, 3)], # 91 1 1
  5: [(1, 3),  # 1 11 91
      (2, 3)], # 11 1 91
  6: [(1, 2),  # 1 1 1991
      (2, 4),  # 11 11 91
      (4, 5)], # 1991 1 1
  7: [(1, 3),  # 1 11 1991
      (2, 3),  # 11 1 1991
      (4, 5),  # 1991 1 11
      (4, 6)], # 1991 11 1
  8: [(2, 4),  # 11 11 1991
      (4, 6)]  # 1991 11 11
}


def date_match(password):
    """ a "date" is recognized as:
      any 3-tuple that starts or ends with a 2- or 4-digit year,
      with 2 or 0 separator chars (1.1.91 or 1191),
      maybe zero-padded (01-01-91 vs 1-1-91),
      a month between 1 and 12,
      a day between 1 and 31.
    
    note: this isn't true date parsing in that "feb 31st" is allowed,
    this doesn't check for leap years, etc.
    
    recipe:
     start with regex to find maybe-dates, then attempt to map the integers
     onto month-day-year to filter the maybe-dates into dates.
     finally, remove matches that are substrings of other matches to reduce noise.
    
    note: instead of using a lazy or greedy regex to find many dates over the full string,
     this uses a ^...$ regex against every substring of the password -- less performant but leads
     to every possible date match.
    """
    matches = []
    maybe_date_no_separator = re.compile(r'^\d{4,8}$')
    maybe_date_with_separator = re.compile(r'''
      ^
      ( \d{1,4} )    # day, month, year
      ( [\s/\\_.-] ) # separator
      ( \d{1,2} )    # day, month
      \2             # same separator
      ( \d{1,4} )    # day, month, year
      $
    ''', re.VERBOSE)

    # dates without separators are between length 4 '1191' and 8 '11111991'
    for i in range(0, len(password) - 3):
        candidates = []
        for j in range(i + 4, min(i + 9, len(password) + 1)):
            token = password[i:j]
            if not token.isdigit():
                continue
            for k, l in DATE_SPLITS[len(token)]:
                dmy = map_ints_to_dmy((int(token[:k]), int(token[k:l]), int(token[l:])))

                if dmy:
                    candidates.append(dmy)
        
            if not len(candidates):
                continue
            # at this point: different possible dmy mappings for the same i,j substring.
            # match the candidate date that likely takes the fewest guesses: a year closest to 2000.
            # (scoring.REFERENCE_YEAR).
            #
            # ie, considering '111504', prefer 11-15-04 to 1-1-1504
            # (interpreting '04' as 2004)
            best_candidate = candidates[0]
            metric = lambda candidate: abs(candidate['year'] - zxcvbn.scoring.REFERENCE_YEAR)
            min_distance = metric(candidates[0])
            for candidate in candidates[1:]:
                distance = metric(candidate)
                if distance < min_distance:
                    best_candidate, min_distance = candidate, distance
            matches.append(dict(pattern='date', token=token,
                                i=i, j=j-1, separator='',
                                year=best_candidate['year'],
                                month=best_candidate['month'],
                                day=best_candidate['day']))

    # dates with separators are between length 6 '1/1/91' and 10 '11/11/1991'
    for i in range(0, len(password) - 5):
        for j in range(i + 6,min(i + 11, len(password) + 1)):
            token = password[i:j]
            rx_match = maybe_date_with_separator.search(token)
            if not rx_match:
                continue
            dmy = map_ints_to_dmy((int(rx_match.group(1)), 
                                   int(rx_match.group(3)), 
                                   int(rx_match.group(4))))
            if not dmy:
                continue 

            matches.append(dict(pattern='date', token=token,
                                i=i, j=j-1, separator=rx_match.group(2),
                                year=dmy['year'], month=dmy['month'], day=dmy['day']))

    # matches now contains all valid date strings in a way that is tricky to capture
    # with regexes only. while thorough, it will contain some unintuitive noise:
    #
    # '2015_06_04', in addition to matching 2015_06_04, will also contain
    # 5(!) other date matches: 15_06_04, 5_06_04, ..., even 2015 (matched as 5/1/2020)
    #
    # to reduce noise, remove date matches that are strict substrings of others
    def is_submatch(match):
        for other_match in matches:
            if match == other_match:
                continue
            if other_match['i'] <= match['i'] and other_match['j'] >= match['j']:
                return True 
        return False
    return [match for match in matches if not is_submatch(match)]


def map_ints_to_dmy(ints):
    """ 
    Given a 3-tuple, discard if:
      middle int is over 31 (for all dmy formats, years are never allowed in the middle)
      middle int is zero
      any int is over the max allowable year
      any int is over two digits but under the min allowable year
      2 ints are over 31, the max allowable day
      2 ints are zero
      all ints are over 12, the max allowable month
    """
    if ints[1] > 31 or ints[1] <= 0:
        return
    over_12 = 0
    over_31 = 0
    under_1 = 0
    for int in ints:
        if 99 < int < DATE_MIN_YEAR or int > DATE_MAX_YEAR:
            return
        over_31 += 1 if int > 31 else 0
        over_12 += 1 if int > 12 else 0
        under_1 += 1 if int <= 0 else 0
    if over_31 >= 2 or over_12 == 3 or under_1 >= 2:
        return

    # first look for a four digit year: yyyy + daymonth or daymonth + yyyy
    possible_year_splits = [
      [ints[2], ints[0:2]],  # year last
      [ints[0], ints[1:3]]   # year first
    ]
    for y, rest in possible_year_splits:
        if DATE_MIN_YEAR <= y <= DATE_MAX_YEAR:
            dm = map_ints_to_dm(rest)
            if dm:
                dm['year'] = y
                return dm
              
            else:
                # for a candidate that includes a four-digit year,
                # when the remaining ints don't match to a day and month,
                # it is not a date.
                return

    # given no four-digit year, two digit years are the most flexible int to match, so
    # try to parse a day-month out of ints[0..1] or ints[1..0]
    for y, rest in possible_year_splits:
        dm = map_ints_to_dm(rest)
        if dm:
            dm['year'] = two_to_four_digit_year(y)
            return dm
 
def map_ints_to_dm(ints):
    for d, m in [ints, ints[::-1]]:
        if 1 <= d <= 31 and 1 <= m <= 12:
            return dict(day=d, month=m)
            
def two_to_four_digit_year(year):
    if year > 99:
        return year
    elif year > 50:
        # 87 -> 1987
        return year + 1900
    else:
        # 15 -> 2015
        return year + 2000


MATCHERS = [
    dictionary_match,
    reversed_dictionary_match,
    l33t_match,
    spatial_match,
    repeat_match, 
    sequence_match,
    regex_match,
    date_match
]


def omnimatch(password, user_inputs=[]):
    _set_user_input_dictionary(user_inputs)

    matches = []
    if len(password):
        for matcher in MATCHERS:
            matches.extend(matcher(password))
        matches.sort(key=lambda x : (x['i'], x['j']))
    return matches
