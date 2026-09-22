import re


def authenticate(pattern, email):
    if '|' in pattern:
        return email in pattern.split('|')
    if '*' in pattern:
        pattern = re.escape(pattern).replace(r'\.\*', r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.\-]*")
        return re.fullmatch(pattern, email)
    return pattern == email


def validate_auth_option(pattern):
    if pattern.count('*') > 1:
        return False
    if '*' in pattern and '|' in pattern:
        return False
    return '*' not in pattern.rsplit('@', 1)[-1]
