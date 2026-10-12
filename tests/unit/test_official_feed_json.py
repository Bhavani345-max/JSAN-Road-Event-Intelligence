"""Official feeds that send slightly broken JSON (7 October 2026).

The City of Toronto's road restrictions feed wrote "Water \\ Sewer" with a lone
backslash, which is not valid JSON, and the whole feed failed to read. A lone
backslash is now read as the backslash it is; valid escapes are left alone,
and a document that is not JSON at all is still an error.
"""

import json

import httpx
import pytest

from connectors.base import ConnectorError
from connectors.official.common import fetch_json, repair_invalid_escapes

# As the feed sent it: a lone backslash between "Water" and "Sewer".
BROKEN = r'[{"description":"Toronto-TMC: Water \ Sewer","fromRoad":"Earlton Rd"}]'


def fetch(body: bytes):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))
    return fetch_json("https://feed.example.org/roads", "ua", client=client)


def test_a_lone_backslash_no_longer_makes_the_feed_unreadable():
    with pytest.raises(json.JSONDecodeError):
        json.loads(BROKEN)
    assert fetch(BROKEN.encode()) == [{"description": "Toronto-TMC: Water \\ Sewer", "fromRoad": "Earlton Rd"}]


def test_valid_escapes_are_left_as_they_are():
    text = r'{"a":"say \"hi\"","b":"C:\\path","c":"line\nnext","d":"\u00e9","e":"x\/y","f":"\\ Sewer"}'
    assert repair_invalid_escapes(text) == text
    assert json.loads(repair_invalid_escapes(text)) == json.loads(text)


def test_a_feed_with_the_tables_toronto_embeds_still_reads():
    # Toronto sends some fields as JSON text inside JSON, escaped, next to the lone backslash.
    body = r'[{"permitType":"{\"tabledata\":[{\"Option\":\"Toronto Water\"}]}","description":"Water \ Sewer"}]'
    [record] = fetch(body.encode())
    assert json.loads(record["permitType"]) == {"tabledata": [{"Option": "Toronto Water"}]}
    assert record["description"] == "Water \\ Sewer"


def test_a_page_that_is_not_json_is_still_an_error():
    with pytest.raises(ConnectorError, match="did not return JSON"):
        fetch(b"<html>maintenance</html>")
