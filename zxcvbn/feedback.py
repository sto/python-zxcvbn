import re
from zxcvbn import scoring

feedback = {
    "warning": "",
    "suggestions":[
        "Use a few words, avoid common phrases.",
        "No need for symbols, digits, or uppercase letters.",  
    ],
}

def get_feedback (score, sequence):
    if len(sequence) == 0:
        return feedback
    if score > 2:
        return dict({"warning": "","suggestions": []})
    longest_match = max(sequence, key=lambda x: len(x['token']))
    feedback = get_match_feedback(longest_match, len(sequence) == 1)
    if not feedback:
        feedback = {
            "warning": "",
            "suggestions":[
                "Add another word or two. Uncommon words are better."
            ],
        }
    return feedback

def get_match_feedback(match, is_sole_match):
    def fun_bruteforce():
        return None
    def fun_dictionary():
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
        if len(match["repeated_char"]) == 1:
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
                    "Avoid recent years."
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
    warning = ""
    suggestions = []
    if match["dictionary_name"] == "passwords":
        if is_sole_match and not match["l33t_entropy"]:
            if match["rank"] <= 10:
                warning = "This is a top-10 common password."
            elif match["rank"] <= 100:
                warning = "This is a top-100 common password."
            else:
                warning = "This is a very common password."
        else:
            warning = "This is similar to a commonly used password."
    elif match["dictionary_name"] == "english":
        if is_sole_match:
            warning = "A word by itself is easy to guess."
    elif match["dictionary_name"] in ["surnames", "male_names", "female_names"]:
        if is_sole_match:
            warning = "Names and surnames by themselves are easy to guess."
        else:
            warning = "Common names and surnames are easy to guess."
    word = match["token"]
    if re.match(scoring.START_UPPER, word):
        suggestions.append("Capitalization doesn't help very much.")
    elif re.match(scoring.ALL_UPPER, word):
        suggestions.append("All-uppercase is almost as easy to guess as all-lowercase.")
    if match["l33t_entropy"]:
        suggestions.append("Predictable substitutions like '@' instead of 'a' don't help very much.")
    return {"warning": warning, "suggestions": suggestions}
