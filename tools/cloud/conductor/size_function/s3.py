"""One object read or written in an S3 bucket with AWS Signature Version 4, standard library only: the size function
reads the conductor's health record with it (it runs with no packages), the conductor writes the record with it, and
`machine.py status` reads it back. Scaleway's object storage takes path-style requests at s3.<region>.scw.cloud.

    s3.get(bucket, key, region, access_key, secret_key)        # the object's bytes, or None when it is not there
    s3.put(bucket, key, body, region, access_key, secret_key)
"""
import datetime
import hashlib
import hmac
import urllib.error
import urllib.parse
import urllib.request

SERVICE = "s3"
TIMEOUT_SECONDS = 30


def endpoint(region):
    return f"https://s3.{region}.scw.cloud"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signing_key(secret_key, day, region):
    """The day's key, derived from the secret as SigV4 says (date, region, service, request)."""
    key = hmac.new(f"AWS4{secret_key}".encode(), day.encode(), hashlib.sha256).digest()
    for part in (region, SERVICE, "aws4_request"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    return key


def signed_headers(method, url, region, access_key, secret_key, payload_hash, now, extra=None):
    """The headers that sign one request: Host, x-amz-date, x-amz-content-sha256, any `extra`, and Authorization."""
    parts = urllib.parse.urlsplit(url)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    headers = {"host": parts.netloc, "x-amz-date": stamp, "x-amz-content-sha256": payload_hash,
               **{name.lower(): value for name, value in (extra or {}).items()}}
    names = sorted(headers)
    canonical = "\n".join([method, urllib.parse.quote(parts.path or "/", safe="/-_.~"), parts.query,
                           "".join(f"{name}:{headers[name].strip()}\n" for name in names), ";".join(names),
                           payload_hash])
    scope = f"{stamp[:8]}/{region}/{SERVICE}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", stamp, scope, digest(canonical.encode())])
    signature = hmac.new(signing_key(secret_key, stamp[:8], region), to_sign.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
                                f"SignedHeaders={';'.join(names)}, Signature={signature}")
    return headers


def object_url(bucket, key, region):
    return f"{endpoint(region)}/{bucket}/{urllib.parse.quote(key, safe='/-_.~')}"


def get(bucket, key, region, access_key, secret_key):
    """The object's bytes, or None when the bucket holds no such key (404)."""
    url = object_url(bucket, key, region)
    now = datetime.datetime.now(datetime.timezone.utc)
    headers = signed_headers("GET", url, region, access_key, secret_key, digest(b""), now)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT_SECONDS) as answer:
            return answer.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def put(bucket, key, body, region, access_key, secret_key):
    """Write `body` (bytes) as the object."""
    url = object_url(bucket, key, region)
    now = datetime.datetime.now(datetime.timezone.utc)
    headers = signed_headers("PUT", url, region, access_key, secret_key, digest(body), now,
                             {"content-type": "application/json"})
    request = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS):
        pass
