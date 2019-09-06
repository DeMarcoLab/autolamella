from io import StringIO

import pytest

import lamella.interactive


@pytest.mark.parametrize(
    "test_input, default, expected",
    [
        (StringIO("\n"), "yes", True),
        (StringIO("\n"), "no", False),
        (StringIO("y\n"), None, True),
        (StringIO("Y\n"), None, True),
        (StringIO("yes\n"), None, True),
        (StringIO("Yes\n"), None, True),
        (StringIO("YES\n"), None, True),
        (StringIO("n\n"), None, False),
        (StringIO("N\n"), None, False),
        (StringIO("no\n"), None, False),
        (StringIO("No\n"), None, False),
        (StringIO("NO\n"), None, False),
    ],
)
def test_ask_user(monkeypatch, test_input, default, expected):
    monkeypatch.setattr("sys.stdin", test_input)
    result = lamella.interactive.ask_user("message", default=default)
    assert result == expected
