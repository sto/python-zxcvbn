# Used for regex matching capitalization
import re
# Used to get the regex patterns for capitalization
# (Used the same way in the original zxcvbn)
from zxcvbn import scoring

# Default feedback value
FEEDBACK = {
    "warning": "",
    "suggestions":[
        "Use a few words, avoid common phrases.",
        "Symbols, digits, or uppercase letters are not required.",
    ],
}

def get_feedback (score, sequence):
    """
    Returns the feedback dictionary consisting of ("warning","suggestions") for the given sequences.
    """
    # Starting feedback
    feedback = FEEDBACK
    if len(sequence) == 0:
        return feedback
    # No feedback if score is good or great
    if score > 2:
        return dict({"warning": "","suggestions": []})
    # Tie feedback to the longest match for longer sequences
    longest_match = max(sequence, key=lambda x: len(x['token']))
    # Get feedback for this match
    feedback = get_match_feedback(longest_match, len(sequence) == 1)
    # If no concrete feedback returned, give more general feedback
    if not feedback:
        feedback = {
            "warning": "",
            "suggestions":[
                "Add another word or two. Uncommon words are better."
            ],
        }
    return feedback

def get_all_feedback (score, sequence):
    """
    Returns the feedback dictionary consisting of {"warnings":[], "suggestions":[]} for the given sequences.
    """
    # Starting feedback
    feedback = dict(warnings=[],suggestions=[])

    if len(sequence) == 0:
        feedback['suggestions'].extend(FEEDBACK['suggestions'])
    
    # No feedback if score is good or great
    elif score <= 2:
        _all_feedback = [fdbk for fdbk in [get_match_feedback(item, len(sequence) == 1) for item in sequence] if fdbk]

        # If no concrete feedback is returned, give more general feedback
        if not _all_feedback:
            feedback["suggestions"].append("Add another word or two. Uncommon words are better.")
              
        # Ensure we don't report the same warning or suggestion twice.
        for item in _all_feedback:
            print(item)
            if item['warning'] and item['warning'] not in feedback['warnings']:
                feedback['warnings'].append(item['warning'])
            for sugg in item['suggestions']:
                if sugg not in feedback['suggestions']:
                    feedback['suggestions'].append(sugg)

    return feedback
        


def get_match_feedback(match, is_sole_match):
    """
    Returns feedback as a dictionary for a certain match
    """
    # Define a number of functions that are used in a look up dictionary
    def fun_bruteforce():
        return None
    def fun_dictionary():
        # If the match is of type dictionary, call specific function
        return get_dictionary_match_feedback(match, is_sole_match)
    def fun_spatial():
        if match["turns"] == 1:
            feedback ={
                "warning": 'Straight rows of keys are easy to guess.',
                "suggestions":[
                     "Use a longer keyboard pattern with more turns."
                ],
            }
        else:
            feedback ={
                "warning": 'Short keyboard patterns are easy to guess.',
                "suggestions":[
                     "Use a longer keyboard pattern with more turns."
                ],
            }
        return feedback
    def fun_repeat():
        if len(match["base_token"]) == 1:
            feedback ={
                "warning": 'Repeats like "aaa" are easy to guess.',
                "suggestions":[
                    "Avoid repeated words and characters."
                ],
            }
        else:
            feedback ={
                    "warning": 'Repeats like "abcabcabc" are only slightly harder to guess than "abc"',
                    "suggestions":[
                        "Avoid repeated words and characters."
                        ],
                    }
        return feedback
    def fun_sequence():
        return {
            "warning": "Sequences like abc or 6543 are easy to guess.",
            "suggestions":[
                "Avoid sequences."
            ],
        }
    def fun_regex():
        if match["regex_name"] == "recent_year":
            return {
                "warning": "Recent years are easy to guess.",
                "suggestions":[
                    "Avoid recent years.",
                    "Avoid years that are associated with you."
                ],
            }
    def fun_date():
        return {
            "warning": "Dates are often easy to guess.",
            "suggestions":[
                "Avoid dates and years that are associated with you."
            ],
        }
    # Dictionary that maps pattern names to funtions that return feedback
    patterns = {
        "bruteforce": fun_bruteforce,
        "dictionary": fun_dictionary,
        "spatial": fun_spatial,
        "repeat": fun_repeat,
        "sequence": fun_sequence,
        "regex": fun_regex,
        "date": fun_date,
    }
    return(patterns[match['pattern']]())

def get_dictionary_match_feedback(match, is_sole_match):
    """
    Returns feedback for a match that is found in a dictionary
    """
    warning = ""
    suggestions = []
    # If the match is a common password
    if match["dictionary_name"] in ["user_inputs"]:
        warning = "Do not use your personal information in your password."

    elif match["dictionary_name"] == "passwords":
        if is_sole_match and not match["l33t"]:
            if match["rank"] <= 10:
                warning = "This is a top-10 common password."
            elif match["rank"] <= 100:
                warning = "This is a top-100 common password."
            else:
                warning = "This is a very common password."
        else:
            warning = "This is similar to a commonly used password."
    # If the match is a common english word
    elif match["dictionary_name"] == "english":
        if is_sole_match:
            warning = "A word by itself is easy to guess."
    # If the match is a common surname/name
    elif match["dictionary_name"] in ["surnames", "male_names", "female_names"]:
        if is_sole_match:
            warning = "Names and surnames by themselves are easy to guess."
        else:
            warning = "Common names and surnames are easy to guess."

    word = match["token"]
    # Variations of the match like UPPERCASES
    if re.match(scoring.START_UPPER, word):
        suggestions.append("Capitalization doesn't help very much.")
    elif re.match(scoring.ALL_UPPER, word):
        suggestions.append("All-uppercase is almost as easy to guess as all-lowercase.")
    if 'reversed' in match and match["reversed"] and len(match['token']) >= 4:
        suggestions.append("Reversed words aren't much harder to guess")
    # Match contains l33t speak substitutions
    if 'l33t' in match and match["l33t"]:
        suggestions.append("Predictable substitutions like '@' instead of 'a' don't help very much.")
    return {"warning": warning, "suggestions": suggestions}
