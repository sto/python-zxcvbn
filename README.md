# python(3)-zxcvbn
This is a fork of fork of python-zxcvbn for python 3. This version has been further updated to port many of the latest features from the current javascript version. The documentation below is out fo date, as the reporting more closely matches the latest version.

The fork of the fork adds I18N and a Spanish dictionary.

The feedback function has been altered to be much more verbose.

This is definitely alpha software, and is badly in need to test cases. The subtle indexing bugs found when porting from coffeescript to python were somewhat difficult to track down. 

See the original repos for more information:
* [zxcvbn](https://github.com/dropbox/zxcvbn)
* [python-zxcvbn](https://github.com/dropbox/python-zxcvbn)
* [python(3)-zxcvbn](https://github.com/sans-serif/python-zxcvbn)

## Why does this exist?
The last commit on the original python-zxcvbn lies a few years back and it is not up to date with zxcvbn.
There exist a number of forks for python 3, but the newer zxcvbn features are missing from those.
For a project I wanted the feature that returns feedback strings with the scoring, so here it is.

## Changes
* Port to python 3
* Implementation of feedback feature from zxcvbn
* Modification of LICENSE.txt to include data

## Usage
The zxcvbn module exports the `password_strength()` function. 
Import zxcvbn, and call 
```python
password_strength(password, user_inputs=[])
```
The function will return a
result dictionary with the following keys:

### Added Keys
This follows the zxcvbn usage.
New is the "feedback" key. It contains a dictionary with the following keys:

Key | Description
------------ | -------------
warning | Contains 0-1 warning string. 
suggestions | Contains a list with 0-N total suggestion strings.

### Old Keys
Key | Description
------------ | -------------
entropy | Bits
crack_time | Estimation of actual crack time, in seconds.
crack_time_display | Same crack time, as a friendlier string: "instant", "6 minutes", "centuries", etc.
score | [0,1,2,3,4] If crack time is less than [10^2, 10^4, 10^6, 10^8, Infinity], useful for implementing a strength bar.
match_sequence | The list of patterns that zxcvbn based the entropy calculation on.
calculation_time | How long it took to calculate an answer, in milliseconds. usually only a few ms.

The optional user_inputs argument is an array of strings that zxcvbn
will add to its internal dictionary. This can be whatever list of
strings you like, but is meant for user inputs from other fields of the
form, like name and email. That way a password that includes the user's
personal info can be heavily penalized. This list is also good for
site-specific vocabulary.

### I18N

To update translations do:

	python3 setup.py extract_messages
	python3 setup.py update_catalog

To compile translations do:

	python3 setup.py compile_catalog
