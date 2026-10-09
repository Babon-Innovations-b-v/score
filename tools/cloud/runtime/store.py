"""Object storage for the container path: one small interface over an S3 bucket (boto3), or over a local folder for
the tests and for a job run by hand without a cloud.

The store is named by five environment variables, which a Kubernetes Secret or `docker run -e` sets:

    SCORE_STORE_ENDPOINT     https://s3.fr-par.scw.cloud, or file:///some/folder for the folder store
    SCORE_STORE_REGION       the bucket's region
    SCORE_STORE_BUCKET       the bucket
    SCORE_STORE_ACCESS_KEY   the key's access half
    SCORE_STORE_SECRET_KEY   the key's secret half (never printed)

`environment(spec)` turns the provider's object_store() into those variables, `from_environment()` opens the store
they name. Keys are plain slash paths (`runs/<run>/<job>/job.json`, `weights/<name>@<revision>.tar`, `code/<sha>.tar.gz`).
"""
import json
import os
import pathlib
import shutil

FIELDS = {"endpoint": "SCORE_STORE_ENDPOINT", "region": "SCORE_STORE_REGION", "bucket": "SCORE_STORE_BUCKET",
          "access_key": "SCORE_STORE_ACCESS_KEY", "secret_key": "SCORE_STORE_SECRET_KEY"}
FOLDER_SCHEME = "file://"


class FolderStore:
    """A store kept in a local folder, each key a file under it."""

    def __init__(self, root):
        self.root = pathlib.Path(root)

    def path(self, key):
        return self.root / key

    def exists(self, key):
        return self.path(key).is_file()

    def download(self, key, destination):
        destination = pathlib.Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.path(key), destination)

    def upload(self, source, key):
        self.path(key).parent.mkdir(parents=True, exist_ok=True)
        partial = self.path(key).with_name(self.path(key).name + ".partial")
        shutil.copyfile(source, partial)
        partial.replace(self.path(key))

    def read_bytes(self, key):
        return self.path(key).read_bytes()

    def write_bytes(self, key, data):
        self.path(key).parent.mkdir(parents=True, exist_ok=True)
        self.path(key).write_bytes(data)

    def keys(self, prefix):
        """Every key that starts with `prefix`, sorted."""
        found = (str(path.relative_to(self.root)) for path in self.root.rglob("*")
                 if path.is_file() and not path.name.endswith(".partial"))
        return sorted(key for key in found if key.startswith(prefix))


## S3-compatible stores cap a multipart upload at 1,000 parts (Scaleway does; AWS allows 10,000), and boto3's 8 MB
## parts would stop an upload at 8 GB: a 15 GB model tar failed so (2026-10-09). Parts grow with the file instead.
MOST_PARTS = 1000
SMALLEST_PART = 8 * 1024 * 1024


def part_size(size):
    """The multipart part size for a file of `size` bytes: boto3's 8 MB, or larger in whole MB so it fits in
    MOST_PARTS parts with room to spare."""
    needed = -(-size // (MOST_PARTS - 50))
    return max(SMALLEST_PART, -(-needed // (1024 * 1024)) * 1024 * 1024)


class BucketStore:
    """A store kept in an S3 bucket (any S3-compatible object storage)."""

    def __init__(self, spec):
        import boto3

        self.bucket = spec["bucket"]
        self.client = boto3.client("s3", endpoint_url=spec["endpoint"], region_name=spec["region"],
                                   aws_access_key_id=spec["access_key"], aws_secret_access_key=spec["secret_key"])

    def exists(self, key):
        import botocore.exceptions

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    def download(self, key, destination):
        destination = pathlib.Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))

    def upload(self, source, key):
        from boto3.s3.transfer import TransferConfig

        size = part_size(pathlib.Path(source).stat().st_size)
        self.client.upload_file(str(source), self.bucket, key,
                                Config=TransferConfig(multipart_threshold=size, multipart_chunksize=size))

    def read_bytes(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def write_bytes(self, key, data):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def keys(self, prefix):
        """Every key that starts with `prefix`, sorted."""
        found = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            found += [item["Key"] for item in page.get("Contents", [])]
        return sorted(found)


def open_store(spec):
    """The store a spec ({endpoint, region, bucket, access_key, secret_key}) names: a folder for a file:// endpoint,
    else the bucket."""
    if spec["endpoint"].startswith(FOLDER_SCHEME):
        return FolderStore(spec["endpoint"][len(FOLDER_SCHEME):])
    return BucketStore(spec)


def from_environment(environ=None):
    """The store the SCORE_STORE_* variables name."""
    environ = os.environ if environ is None else environ
    needed = FIELDS.values()
    if environ.get(FIELDS["endpoint"], "").startswith(FOLDER_SCHEME):
        needed = [FIELDS["endpoint"]]
    missing = [name for name in needed if not environ.get(name)]
    if missing:
        raise SystemExit(f"the store is not named: {', '.join(missing)} unset")
    return open_store({field: environ.get(name, "") for field, name in FIELDS.items()})


def environment(spec):
    """The SCORE_STORE_* variables for a store spec (the provider's object_store())."""
    return {name: spec[field] for field, name in FIELDS.items()}


def read_json(store, key):
    return json.loads(store.read_bytes(key))


def write_json(store, key, value):
    store.write_bytes(key, json.dumps(value, indent=1).encode())
